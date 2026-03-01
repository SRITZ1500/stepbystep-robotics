"""
Execution Tracker component for StepbyStep:ROBOTICS.

This module provides real-time task execution monitoring, step recording,
and advanced anomaly detection capabilities.

Requirements:
- 4.1: System shall assign unique execution IDs
- 4.2: System shall record each execution step with timestamp, action, state, outcome
- 4.3: System shall maintain complete execution traces
- 4.4: System shall detect execution anomalies
- 22.1: System shall detect execution deviations from expected behavior
- 22.2: System shall classify anomaly type and severity
- 22.3: System shall record anomalies in trace with context
- 22.4: System shall alert operators for critical anomalies
- 22.5: System shall provide anomaly investigation tools
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from ..models import (
    ExecutionTrace,
    ExecutionStepRecord,
    ExecutionStatus,
    StepStatus,
    RobotState,
    Anomaly,
)


class TrackingSession:
    """Active tracking session for an execution."""
    
    def __init__(self, execution_id: str, task_id: str, robot_id: UUID):
        """Initialize tracking session."""
        self.execution_id = execution_id
        self.task_id = task_id
        self.robot_id = robot_id
        self.start_time = datetime.now()
        self.is_active = True


class AnomalyReport:
    """Report of detected anomalies during execution."""
    
    def __init__(self, execution_id: str, anomalies: list, critical_count: int = 0):
        """Initialize anomaly report."""
        self.execution_id = execution_id
        self.anomalies = anomalies
        self.timestamp = datetime.now()
        self.critical_count = critical_count
        self.requires_operator_alert = critical_count > 0


class ExecutionTracker:
    """
    Monitors task execution in real-time and maintains execution history.
    
    The ExecutionTracker is responsible for:
    - Initializing tracking with unique execution IDs (Requirement 4.1)
    - Recording each execution step with timestamps and state snapshots (Requirement 4.2)
    - Maintaining complete execution traces (Requirement 4.3)
    - Detecting anomalies during execution (Requirement 4.4)
    """
    
    def __init__(self):
        """Initialize the execution tracker."""
        self._active_sessions: Dict[str, TrackingSession] = {}
        self._traces: Dict[str, ExecutionTrace] = {}
        self._anomaly_thresholds = {
            'duration_multiplier': 2.0,  # Alert if step takes 2x expected duration
            'state_deviation_threshold': 0.1,  # 10% deviation threshold
            'critical_duration_multiplier': 3.0,  # Critical if step takes 3x expected
            'battery_drain_rate_threshold': 0.2,  # Max 20% battery drain per step
            'position_jump_threshold': 5.0,  # Max 5 units position change per step
        }
        self._operator_alerts: list = []  # Store critical alerts for operators
    
    def startTracking(
        self,
        task_id: str,
        robot_id: UUID,
        initial_state: RobotState,
        execution_id: Optional[str] = None
    ) -> TrackingSession:
        """
        Initialize tracking for a new task execution.
        
        Creates a unique execution ID and initializes an execution trace.
        
        Args:
            task_id: ID of the task being executed
            robot_id: ID of the robot executing the task
            initial_state: Initial robot state at execution start
            execution_id: Optional custom execution ID (generates UUID if not provided)
        
        Returns:
            TrackingSession: Active tracking session
        
        Validates: Requirement 4.1 - Unique execution ID assignment
        """
        # Generate unique execution ID if not provided
        if execution_id is None:
            execution_id = str(uuid4())
        
        # Validate execution_id is unique
        if execution_id in self._active_sessions or execution_id in self._traces:
            raise ValueError(f"Execution ID {execution_id} already exists")
        
        # Create tracking session
        session = TrackingSession(execution_id, task_id, robot_id)
        self._active_sessions[execution_id] = session
        
        # Initialize execution trace
        trace = ExecutionTrace(
            execution_id=execution_id,
            task_id=task_id,
            robot_id=robot_id,
            start_time=session.start_time,
            end_time=None,
            status=ExecutionStatus.IN_PROGRESS,
            steps=[],
            state_history=[initial_state],
            anomalies=[],
            performance_metrics=None
        )
        self._traces[execution_id] = trace
        
        return session
    
    def recordStep(
        self,
        execution_id: str,
        step_record: ExecutionStepRecord
    ) -> None:
        """
        Record a completed execution step.
        
        Adds the step record to the execution trace and updates state history.
        
        Args:
            execution_id: ID of the execution
            step_record: Complete record of the executed step
        
        Raises:
            ValueError: If execution_id is not found or session is not active
        
        Validates: Requirement 4.2 - Record each step with timestamp, action, state, outcome
        """
        # Validate execution exists
        if execution_id not in self._traces:
            raise ValueError(f"Execution ID {execution_id} not found")
        
        # Validate session is active
        if execution_id not in self._active_sessions:
            raise ValueError(f"No active session for execution ID {execution_id}")
        
        trace = self._traces[execution_id]
        
        # Validate chronological ordering
        if trace.steps:
            last_step = trace.steps[-1]
            if step_record.start_time < last_step.end_time:
                raise ValueError(
                    f"Step start time {step_record.start_time} is before "
                    f"previous step end time {last_step.end_time}"
                )
        
        # Add step to trace
        trace.steps.append(step_record)
        
        # Update state history with output state
        if step_record.output_state not in trace.state_history:
            trace.state_history.append(step_record.output_state)
    
    def getCurrentStatus(self, execution_id: str) -> ExecutionStatus:
        """
        Get the current status of an execution.
        
        Args:
            execution_id: ID of the execution
        
        Returns:
            ExecutionStatus: Current execution status
        
        Raises:
            ValueError: If execution_id is not found
        """
        if execution_id not in self._traces:
            raise ValueError(f"Execution ID {execution_id} not found")
        
        return self._traces[execution_id].status
    
    def getExecutionTrace(self, execution_id: str) -> ExecutionTrace:
        """
        Retrieve the complete execution trace.
        
        Args:
            execution_id: ID of the execution
        
        Returns:
            ExecutionTrace: Complete execution trace
        
        Raises:
            ValueError: If execution_id is not found
        
        Validates: Requirement 4.3 - Maintain complete execution traces
        """
        if execution_id not in self._traces:
            raise ValueError(f"Execution ID {execution_id} not found")
        
        return self._traces[execution_id]
    
    def detectAnomaly(
        self,
        execution_id: str,
        expected_duration: Optional[float] = None
    ) -> AnomalyReport:
        """
        Detect anomalies in the current execution.
        
        Analyzes the execution trace for:
        - Unexpected state transitions
        - Timing violations (steps taking too long)
        - Constraint violations
        - Excessive battery drain
        - Abnormal position jumps
        - Error flag patterns
        
        Args:
            execution_id: ID of the execution
            expected_duration: Expected duration for comparison (optional)
        
        Returns:
            AnomalyReport: Report of detected anomalies with classification
        
        Raises:
            ValueError: If execution_id is not found
        
        Validates: Requirements 22.1, 22.2, 22.3, 22.4, 22.5
        """
        if execution_id not in self._traces:
            raise ValueError(f"Execution ID {execution_id} not found")
        
        trace = self._traces[execution_id]
        detected_anomalies = []
        critical_count = 0
        
        # 1. Detect timing violations with severity classification
        for step in trace.steps:
            if hasattr(step, 'expected_duration'):
                expected = getattr(step, 'expected_duration', None)
                if expected and step.actual_duration > expected * self._anomaly_thresholds['duration_multiplier']:
                    # Classify severity based on how much it exceeded
                    ratio = step.actual_duration / expected
                    if ratio >= self._anomaly_thresholds['critical_duration_multiplier']:
                        severity = "CRITICAL"
                        critical_count += 1
                    else:
                        severity = "WARNING"
                    
                    anomaly = Anomaly(
                        anomaly_type="TIMING_VIOLATION",
                        severity=severity,
                        description=f"Step {step.step_id} took {step.actual_duration:.2f}s, "
                                  f"expected {expected:.2f}s ({ratio:.1f}x threshold)",
                        timestamp=step.end_time,
                        context={
                            'step_id': step.step_id,
                            'actual_duration': step.actual_duration,
                            'expected_duration': expected,
                            'duration_ratio': ratio,
                            'threshold_multiplier': self._anomaly_thresholds['duration_multiplier'],
                            'classification': 'execution_performance'
                        }
                    )
                    detected_anomalies.append(anomaly)
        
        # 2. Detect unexpected state transitions with enhanced checks
        for i in range(len(trace.state_history) - 1):
            current_state = trace.state_history[i]
            next_state = trace.state_history[i + 1]
            
            # Check for impossible battery level increase
            if next_state.battery_level > current_state.battery_level + 0.01:
                anomaly = Anomaly(
                    anomaly_type="UNEXPECTED_STATE_TRANSITION",
                    severity="CRITICAL",
                    description=f"Battery level increased from {current_state.battery_level:.2f} "
                              f"to {next_state.battery_level:.2f} without charging",
                    timestamp=next_state.timestamp,
                    context={
                        'previous_battery': current_state.battery_level,
                        'current_battery': next_state.battery_level,
                        'state_index': i,
                        'classification': 'state_consistency'
                    }
                )
                detected_anomalies.append(anomaly)
                critical_count += 1
            
            # Check for excessive battery drain
            battery_drain = current_state.battery_level - next_state.battery_level
            if battery_drain > self._anomaly_thresholds['battery_drain_rate_threshold']:
                severity = "CRITICAL" if battery_drain > 0.3 else "WARNING"
                if severity == "CRITICAL":
                    critical_count += 1
                
                anomaly = Anomaly(
                    anomaly_type="EXCESSIVE_BATTERY_DRAIN",
                    severity=severity,
                    description=f"Excessive battery drain: {battery_drain:.2%} in single step "
                              f"(threshold: {self._anomaly_thresholds['battery_drain_rate_threshold']:.2%})",
                    timestamp=next_state.timestamp,
                    context={
                        'battery_drain': battery_drain,
                        'previous_battery': current_state.battery_level,
                        'current_battery': next_state.battery_level,
                        'threshold': self._anomaly_thresholds['battery_drain_rate_threshold'],
                        'classification': 'resource_consumption'
                    }
                )
                detected_anomalies.append(anomaly)
            
            # Check for abnormal position jumps
            position_delta = (
                (next_state.position.x - current_state.position.x) ** 2 +
                (next_state.position.y - current_state.position.y) ** 2 +
                (next_state.position.z - current_state.position.z) ** 2
            ) ** 0.5
            
            if position_delta > self._anomaly_thresholds['position_jump_threshold']:
                severity = "CRITICAL" if position_delta > 10.0 else "WARNING"
                if severity == "CRITICAL":
                    critical_count += 1
                
                anomaly = Anomaly(
                    anomaly_type="ABNORMAL_POSITION_JUMP",
                    severity=severity,
                    description=f"Abnormal position jump: {position_delta:.2f} units "
                              f"(threshold: {self._anomaly_thresholds['position_jump_threshold']:.1f})",
                    timestamp=next_state.timestamp,
                    context={
                        'position_delta': position_delta,
                        'previous_position': {
                            'x': current_state.position.x,
                            'y': current_state.position.y,
                            'z': current_state.position.z
                        },
                        'current_position': {
                            'x': next_state.position.x,
                            'y': next_state.position.y,
                            'z': next_state.position.z
                        },
                        'threshold': self._anomaly_thresholds['position_jump_threshold'],
                        'classification': 'motion_behavior'
                    }
                )
                detected_anomalies.append(anomaly)
            
            # Check for new error flags with pattern analysis
            new_errors = next_state.error_flags - current_state.error_flags
            if new_errors:
                # Classify severity based on error types
                critical_errors = {'MOTOR_FAILURE', 'SENSOR_CRITICAL', 'SAFETY_VIOLATION', 'COLLISION_DETECTED'}
                has_critical = bool(new_errors & critical_errors)
                severity = "CRITICAL" if has_critical else "WARNING"
                if severity == "CRITICAL":
                    critical_count += 1
                
                anomaly = Anomaly(
                    anomaly_type="ERROR_FLAG_DETECTED",
                    severity=severity,
                    description=f"New error flags detected: {', '.join(sorted(new_errors))}",
                    timestamp=next_state.timestamp,
                    context={
                        'new_errors': sorted(list(new_errors)),
                        'all_errors': sorted(list(next_state.error_flags)),
                        'is_critical_error': has_critical,
                        'classification': 'system_health'
                    }
                )
                detected_anomalies.append(anomaly)
        
        # 3. Detect constraint violations with enhanced context
        for step in trace.steps:
            if step.deviations:
                for deviation in step.deviations:
                    if deviation.severity in ['HIGH', 'CRITICAL']:
                        is_critical = deviation.severity == 'CRITICAL'
                        if is_critical:
                            critical_count += 1
                        
                        anomaly = Anomaly(
                            anomaly_type="CONSTRAINT_VIOLATION",
                            severity=deviation.severity,
                            description=f"Step {step.step_id} violated constraint: "
                                      f"{deviation.metric} expected {deviation.expected}, "
                                      f"got {deviation.actual}",
                            timestamp=step.end_time,
                            context={
                                'step_id': step.step_id,
                                'metric': deviation.metric,
                                'expected': deviation.expected,
                                'actual': deviation.actual,
                                'deviation_magnitude': abs(deviation.actual - deviation.expected) if isinstance(deviation.actual, (int, float)) and isinstance(deviation.expected, (int, float)) else None,
                                'classification': 'constraint_compliance'
                            }
                        )
                        detected_anomalies.append(anomaly)
        
        # 4. Detect execution pattern anomalies
        if len(trace.steps) > 0:
            # Check for repeated step failures
            failed_steps = [s for s in trace.steps if s.status == StepStatus.FAILED]
            if len(failed_steps) > len(trace.steps) * 0.3:  # More than 30% failures
                anomaly = Anomaly(
                    anomaly_type="HIGH_FAILURE_RATE",
                    severity="CRITICAL",
                    description=f"High step failure rate: {len(failed_steps)}/{len(trace.steps)} "
                              f"({len(failed_steps)/len(trace.steps):.1%}) steps failed",
                    timestamp=datetime.now(),
                    context={
                        'failed_count': len(failed_steps),
                        'total_count': len(trace.steps),
                        'failure_rate': len(failed_steps) / len(trace.steps),
                        'failed_step_ids': [s.step_id for s in failed_steps],
                        'classification': 'execution_reliability'
                    }
                )
                detected_anomalies.append(anomaly)
                critical_count += 1
            
            # Check for excessive retries
            high_retry_steps = [s for s in trace.steps if hasattr(s, 'retry_count') and s.retry_count > 2]
            if high_retry_steps:
                severity = "CRITICAL" if any(s.retry_count > 5 for s in high_retry_steps) else "WARNING"
                if severity == "CRITICAL":
                    critical_count += 1
                
                anomaly = Anomaly(
                    anomaly_type="EXCESSIVE_RETRIES",
                    severity=severity,
                    description=f"{len(high_retry_steps)} steps required excessive retries",
                    timestamp=datetime.now(),
                    context={
                        'high_retry_steps': [
                            {'step_id': s.step_id, 'retry_count': s.retry_count}
                            for s in high_retry_steps
                        ],
                        'max_retries': max(s.retry_count for s in high_retry_steps),
                        'classification': 'execution_reliability'
                    }
                )
                detected_anomalies.append(anomaly)
        
        # Add detected anomalies to trace (avoid duplicates)
        for anomaly in detected_anomalies:
            if anomaly not in trace.anomalies:
                trace.anomalies.append(anomaly)
        
        # Alert operators for critical anomalies
        if critical_count > 0:
            self._alertOperator(execution_id, detected_anomalies, critical_count)
        
        return AnomalyReport(execution_id, detected_anomalies, critical_count)
    
    def finishTracking(
        self,
        execution_id: str,
        final_status: ExecutionStatus,
        final_state: RobotState
    ) -> ExecutionTrace:
        """
        Finish tracking and finalize the execution trace.
        
        Args:
            execution_id: ID of the execution
            final_status: Final execution status
            final_state: Final robot state
        
        Returns:
            ExecutionTrace: Finalized execution trace
        
        Raises:
            ValueError: If execution_id is not found or session is not active
        """
        if execution_id not in self._traces:
            raise ValueError(f"Execution ID {execution_id} not found")
        
        if execution_id not in self._active_sessions:
            raise ValueError(f"No active session for execution ID {execution_id}")
        
        trace = self._traces[execution_id]
        session = self._active_sessions[execution_id]
        
        # Update trace with final information
        trace.end_time = datetime.now()
        trace.status = final_status
        
        # Add final state if not already in history
        if final_state not in trace.state_history:
            trace.state_history.append(final_state)
        
        # Mark session as inactive
        session.is_active = False
        del self._active_sessions[execution_id]
        
        return trace
    
    def abortTracking(
        self,
        execution_id: str,
        reason: str,
        final_state: RobotState
    ) -> ExecutionTrace:
        """
        Abort tracking due to execution failure or interruption.
        
        Args:
            execution_id: ID of the execution
            reason: Reason for abort
            final_state: Final robot state at abort
        
        Returns:
            ExecutionTrace: Aborted execution trace
        """
        if execution_id not in self._traces:
            raise ValueError(f"Execution ID {execution_id} not found")
        
        trace = self._traces[execution_id]
        
        # Add abort anomaly
        abort_anomaly = Anomaly(
            anomaly_type="EXECUTION_ABORTED",
            severity="CRITICAL",
            description=f"Execution aborted: {reason}",
            timestamp=datetime.now(),
            context={'reason': reason, 'classification': 'execution_control'}
        )
        trace.anomalies.append(abort_anomaly)
        
        # Alert operators about critical abort
        self._alertOperator(execution_id, [abort_anomaly], 1)
        
        # Finish tracking with ABORTED status
        return self.finishTracking(execution_id, ExecutionStatus.ABORTED, final_state)
    
    def _alertOperator(
        self,
        execution_id: str,
        anomalies: list,
        critical_count: int
    ) -> None:
        """
        Alert operators about critical anomalies.
        
        This method creates operator alerts for critical anomalies that require
        immediate attention. In a production system, this would integrate with
        alerting systems (e.g., PagerDuty, Slack, email).
        
        Args:
            execution_id: ID of the execution with anomalies
            anomalies: List of detected anomalies
            critical_count: Number of critical anomalies
        
        Validates: Requirement 22.4 - Alert operators for critical anomalies
        """
        critical_anomalies = [a for a in anomalies if a.severity == "CRITICAL"]
        
        if not critical_anomalies:
            return
        
        alert = {
            'execution_id': execution_id,
            'timestamp': datetime.now(),
            'critical_count': critical_count,
            'total_anomalies': len(anomalies),
            'anomalies': [
                {
                    'type': a.anomaly_type,
                    'severity': a.severity,
                    'description': a.description,
                    'timestamp': a.timestamp,
                    'context': a.context
                }
                for a in critical_anomalies
            ],
            'alert_level': 'URGENT' if critical_count > 3 else 'HIGH',
            'recommended_action': self._getRecommendedAction(critical_anomalies)
        }
        
        self._operator_alerts.append(alert)
        
        # In production, this would trigger actual alerts:
        # - Send to monitoring system (e.g., Prometheus Alertmanager)
        # - Notify via communication channels (Slack, PagerDuty, email)
        # - Log to centralized logging system
        # - Update dashboard with alert status
    
    def _getRecommendedAction(self, critical_anomalies: list) -> str:
        """
        Generate recommended action based on critical anomalies.
        
        Args:
            critical_anomalies: List of critical anomalies
        
        Returns:
            str: Recommended action for operators
        """
        anomaly_types = {a.anomaly_type for a in critical_anomalies}
        
        if 'EXECUTION_ABORTED' in anomaly_types:
            return "Investigate abort reason and verify robot safety state"
        elif 'UNEXPECTED_STATE_TRANSITION' in anomaly_types:
            return "Check robot sensors and state consistency; may require recalibration"
        elif 'HIGH_FAILURE_RATE' in anomaly_types:
            return "Review task specification and robot capabilities; consider task redesign"
        elif 'ABNORMAL_POSITION_JUMP' in anomaly_types:
            return "Verify robot localization and motion control systems"
        elif 'ERROR_FLAG_DETECTED' in anomaly_types:
            return "Check robot hardware status and error logs for diagnostics"
        elif 'EXCESSIVE_BATTERY_DRAIN' in anomaly_types:
            return "Inspect battery health and power consumption patterns"
        else:
            return "Review execution trace and anomaly details for root cause analysis"
    
    def getOperatorAlerts(self, execution_id: Optional[str] = None) -> list:
        """
        Retrieve operator alerts for critical anomalies.
        
        Args:
            execution_id: Optional execution ID to filter alerts
        
        Returns:
            list: List of operator alerts
        
        Validates: Requirement 22.5 - Provide anomaly investigation tools
        """
        if execution_id is None:
            return self._operator_alerts
        
        return [alert for alert in self._operator_alerts if alert['execution_id'] == execution_id]
    
    def clearOperatorAlerts(self, execution_id: Optional[str] = None) -> None:
        """
        Clear operator alerts after they have been acknowledged.
        
        Args:
            execution_id: Optional execution ID to clear specific alerts
        """
        if execution_id is None:
            self._operator_alerts.clear()
        else:
            self._operator_alerts = [
                alert for alert in self._operator_alerts
                if alert['execution_id'] != execution_id
            ]
    
    def getAnomalyStatistics(self, execution_id: str) -> dict:
        """
        Get statistical summary of anomalies for an execution.
        
        Provides investigation tools for analyzing anomaly patterns.
        
        Args:
            execution_id: ID of the execution
        
        Returns:
            dict: Statistical summary of anomalies
        
        Raises:
            ValueError: If execution_id is not found
        
        Validates: Requirement 22.5 - Provide anomaly investigation tools
        """
        if execution_id not in self._traces:
            raise ValueError(f"Execution ID {execution_id} not found")
        
        trace = self._traces[execution_id]
        anomalies = trace.anomalies
        
        if not anomalies:
            return {
                'total_count': 0,
                'by_severity': {},
                'by_type': {},
                'by_classification': {},
                'critical_count': 0,
                'timeline': []
            }
        
        # Count by severity
        by_severity = {}
        for anomaly in anomalies:
            by_severity[anomaly.severity] = by_severity.get(anomaly.severity, 0) + 1
        
        # Count by type
        by_type = {}
        for anomaly in anomalies:
            by_type[anomaly.anomaly_type] = by_type.get(anomaly.anomaly_type, 0) + 1
        
        # Count by classification (from context)
        by_classification = {}
        for anomaly in anomalies:
            classification = anomaly.context.get('classification', 'unclassified')
            by_classification[classification] = by_classification.get(classification, 0) + 1
        
        # Create timeline
        timeline = [
            {
                'timestamp': a.timestamp,
                'type': a.anomaly_type,
                'severity': a.severity,
                'description': a.description
            }
            for a in sorted(anomalies, key=lambda x: x.timestamp)
        ]
        
        return {
            'total_count': len(anomalies),
            'by_severity': by_severity,
            'by_type': by_type,
            'by_classification': by_classification,
            'critical_count': by_severity.get('CRITICAL', 0),
            'timeline': timeline
        }
