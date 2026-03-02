"""
End-to-End Workflow Integration
Demonstrates complete StepbyStep:ROBOTICS system operation
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from .models import (
    RobotState, TaskSpecification, ExecutionTrace, 
    PerformanceMetrics
)
from .improvement.regression_detector import RegressionReport
from .behavior.state_observer import StateObserver
from .behavior.action_translator import ActionTranslator
from .workflow.task_spec_engine import TaskSpecEngine
from .workflow.execution_tracker import ExecutionTracker
from .workflow.runbook_manager import RunbookManager
from .improvement.evaluation_engine import EvaluationEngine
from .improvement.regression_detector import RegressionDetector
from .improvement.governance_system import GovernanceSystem


@dataclass
class WorkflowResult:
    """Result of an end-to-end workflow execution"""
    success: bool
    execution_id: str
    trace: Optional[ExecutionTrace]
    metrics: Optional[PerformanceMetrics]
    regression_detected: bool
    regression_report: Optional[RegressionReport]
    governance_decision: str
    error: Optional[str] = None


class ObservabilityPipeline:
    """
    Complete observability pipeline: observe → record
    Demonstrates Behavior Layer integration
    """
    
    def __init__(self):
        self.observer = StateObserver()
    
    def observe_and_translate_stream(
        self,
        robot_id: str,
        duration_seconds: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Observe robot state stream
        
        Args:
            robot_id: Robot identifier
            duration_seconds: How long to observe
            
        Returns:
            List of observations with timestamps
        """
        from uuid import UUID
        from datetime import datetime, timedelta
        from .models import Vector3D, Quaternion
        
        observations = []
        robot_uuid = UUID(int=hash(robot_id) % (2**128))
        
        # Simulate observation stream by creating sample states
        start_time = datetime.now()
        num_samples = int(duration_seconds * 2)  # 2 Hz sampling
        
        for i in range(num_samples):
            timestamp = start_time + timedelta(seconds=i * 0.5)
            
            # Create sample raw state data
            raw_data = {
                'timestamp': timestamp,
                'position': Vector3D(x=float(i), y=0.0, z=1.0),
                'orientation': Quaternion(w=1.0, x=0.0, y=0.0, z=0.0),
                'joint_states': {},
                'sensor_readings': {'camera': 1.0},
                'actuator_states': {},
                'battery_level': 0.95,
                'error_flags': set()
            }
            
            # Normalize and record state
            state = self.observer.normalizeAndRecordState(robot_uuid, raw_data)
            
            observations.append({
                'timestamp': state.timestamp,
                'robot_id': robot_id,
                'raw_state': state,
                'confidence': 1.0  # State observation is always high confidence
            })
        
        return observations


class TaskExecutionWorkflow:
    """
    Complete task execution workflow with tracking and evaluation
    Demonstrates Workflow Layer integration
    """
    
    def __init__(self):
        self.spec_engine = TaskSpecEngine()
        self.tracker = ExecutionTracker()
        self.evaluator = EvaluationEngine()
    
    def execute_task_with_tracking(
        self,
        task_spec: TaskSpecification,
        robot_id: str
    ) -> WorkflowResult:
        """
        Execute task with full tracking and evaluation
        
        Args:
            task_spec: Task specification to execute
            robot_id: Robot to execute on
            
        Returns:
            WorkflowResult with execution details
        """
        try:
            # Validate task specification
            if not self.spec_engine.validate_spec(task_spec):
                return WorkflowResult(
                    success=False,
                    execution_id="",
                    trace=None,
                    metrics=None,
                    regression_detected=False,
                    regression_report=None,
                    governance_decision="REJECTED",
                    error="Invalid task specification"
                )
            
            # Start execution tracking
            execution_id = self.tracker.start_tracking(task_spec, robot_id)
            
            # Execute task (simplified - would integrate with actual robot)
            # In production, this calls the robot controller
            trace = self._simulate_execution(task_spec, robot_id, execution_id)
            
            # Evaluate execution
            metrics = self.evaluator.evaluate_execution(trace)
            
            return WorkflowResult(
                success=trace.status == "completed",
                execution_id=execution_id,
                trace=trace,
                metrics=metrics,
                regression_detected=False,
                regression_report=None,
                governance_decision="APPROVED"
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                execution_id="",
                trace=None,
                metrics=None,
                regression_detected=False,
                regression_report=None,
                governance_decision="ERROR",
                error=str(e)
            )
    
    def _simulate_execution(
        self,
        task_spec: TaskSpecification,
        robot_id: str,
        execution_id: str
    ) -> ExecutionTrace:
        """Simulate task execution for demo purposes"""
        from .workflow.task_execution import execute_task_pipeline
        return execute_task_pipeline(task_spec, robot_id)


class RegressionDetectionWorkflow:
    """
    Complete regression detection workflow
    Demonstrates Improvement Layer integration
    """
    
    def __init__(self):
        self.evaluator = EvaluationEngine()
        self.detector = RegressionDetector()
    
    def detect_and_report_regression(
        self,
        task_id: str,
        recent_traces: List[ExecutionTrace]
    ) -> WorkflowResult:
        """
        Evaluate recent executions and detect regressions
        
        Args:
            task_id: Task identifier
            recent_traces: Recent execution traces to analyze
            
        Returns:
            WorkflowResult with regression analysis
        """
        try:
            # Evaluate all traces
            metrics_list = [
                self.evaluator.evaluate_execution(trace)
                for trace in recent_traces
            ]
            
            # Detect regression
            regression_report = self.detector.detect_regression(
                task_id=task_id,
                recent_metrics=metrics_list
            )
            
            return WorkflowResult(
                success=True,
                execution_id="",
                trace=None,
                metrics=None,
                regression_detected=regression_report.regression_detected,
                regression_report=regression_report,
                governance_decision="ANALYZED"
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                execution_id="",
                trace=None,
                metrics=None,
                regression_detected=False,
                regression_report=None,
                governance_decision="ERROR",
                error=str(e)
            )


class PolicyGovernedExecutionWorkflow:
    """
    Complete policy-governed execution workflow
    Demonstrates governance integration across all layers
    """
    
    def __init__(self):
        self.governance = GovernanceSystem()
        self.spec_engine = TaskSpecEngine()
        self.tracker = ExecutionTracker()
        self.evaluator = EvaluationEngine()
        self.detector = RegressionDetector()
    
    def execute_with_governance(
        self,
        task_spec: TaskSpecification,
        robot_id: str,
        operator_id: str
    ) -> WorkflowResult:
        """
        Execute task with full governance enforcement
        
        Args:
            task_spec: Task to execute
            robot_id: Robot identifier
            operator_id: Operator requesting execution
            
        Returns:
            WorkflowResult with governance decisions
        """
        try:
            # Check governance policy before execution
            # For demo purposes, use simple risk-based policy
            risk_level = 'medium'  # Default risk level
            
            # Try to extract risk level from task metadata if available
            if hasattr(task_spec, 'metadata') and isinstance(task_spec.metadata, dict):
                risk_level = task_spec.metadata.get('risk_level', 'medium')
            
            policy_decision = self.governance.enforce_policy(
                action_type="task_execution",
                context={
                    'task_id': task_spec.task_id,
                    'robot_id': robot_id,
                    'operator_id': operator_id,
                    'risk_level': risk_level
                }
            )
            
            if policy_decision.decision == "DENY":
                return WorkflowResult(
                    success=False,
                    execution_id="",
                    trace=None,
                    metrics=None,
                    regression_detected=False,
                    regression_report=None,
                    governance_decision="DENIED",
                    error=f"Policy violation: {policy_decision.reason}"
                )
            
            if policy_decision.decision == "REQUIRE_APPROVAL":
                # In production, this would wait for approval
                return WorkflowResult(
                    success=False,
                    execution_id="",
                    trace=None,
                    metrics=None,
                    regression_detected=False,
                    regression_report=None,
                    governance_decision="PENDING_APPROVAL",
                    error="Requires administrator approval"
                )
            
            # Execute task
            execution_id = self.tracker.start_tracking(task_spec, robot_id)
            
            # Audit the execution start
            self.governance.audit_action(
                action_type="task_execution_started",
                actor_id=operator_id,
                resource_id=execution_id,
                details={'task_id': task_spec.task_id, 'robot_id': robot_id}
            )
            
            # Simulate execution
            from .workflow.task_execution import execute_task_pipeline
            trace = execute_task_pipeline(task_spec, robot_id)
            
            # Evaluate
            metrics = self.evaluator.evaluate_execution(trace)
            
            # Audit completion
            self.governance.audit_action(
                action_type="task_execution_completed",
                actor_id=operator_id,
                resource_id=execution_id,
                details={
                    'status': trace.status,
                    'duration': metrics.duration_seconds,
                    'success_rate': metrics.success_rate
                }
            )
            
            return WorkflowResult(
                success=trace.status == "completed",
                execution_id=execution_id,
                trace=trace,
                metrics=metrics,
                regression_detected=False,
                regression_report=None,
                governance_decision="APPROVED"
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                execution_id="",
                trace=None,
                metrics=None,
                regression_detected=False,
                regression_report=None,
                governance_decision="ERROR",
                error=str(e)
            )


class CompleteSystemWorkflow:
    """
    Demonstrates complete system integration across all three layers
    This is the end-to-end demo for Amazon
    """
    
    def __init__(self):
        self.observability = ObservabilityPipeline()
        self.task_execution = TaskExecutionWorkflow()
        self.regression = RegressionDetectionWorkflow()
        self.governed = PolicyGovernedExecutionWorkflow()
    
    def run_complete_workflow(
        self,
        task_spec: TaskSpecification,
        robot_id: str,
        operator_id: str
    ) -> Dict[str, Any]:
        """
        Run complete workflow demonstrating all system capabilities
        
        This is the money shot for the Amazon pitch:
        1. Observe robot state
        2. Execute task with governance
        3. Track and evaluate
        4. Detect regressions
        5. Generate compliance report
        
        Args:
            task_spec: Task to execute
            robot_id: Robot identifier
            operator_id: Operator identifier
            
        Returns:
            Complete workflow results
        """
        results = {
            'workflow_id': f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'phases': {}
        }
        
        # Phase 1: Observe robot state
        observations = self.observability.observe_and_translate_stream(
            robot_id=robot_id,
            duration_seconds=5.0
        )
        results['phases']['observation'] = {
            'success': True,
            'observation_count': len(observations),
            'sample': observations[:3] if observations else []
        }
        
        # Phase 2: Execute task with governance
        execution_result = self.governed.execute_with_governance(
            task_spec=task_spec,
            robot_id=robot_id,
            operator_id=operator_id
        )
        results['phases']['execution'] = {
            'success': execution_result.success,
            'execution_id': execution_result.execution_id,
            'governance_decision': execution_result.governance_decision,
            'metrics': execution_result.metrics.__dict__ if execution_result.metrics else None
        }
        
        # Phase 3: Regression detection (if execution succeeded)
        if execution_result.success and execution_result.trace:
            regression_result = self.regression.detect_and_report_regression(
                task_id=task_spec.task_id,
                recent_traces=[execution_result.trace]
            )
            results['phases']['regression_detection'] = {
                'success': regression_result.success,
                'regression_detected': regression_result.regression_detected,
                'report': regression_result.regression_report.__dict__ if regression_result.regression_report else None
            }
        
        # Phase 4: Generate compliance report
        compliance_report = self.governed.governance.generate_compliance_report(
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        results['phases']['compliance'] = {
            'total_actions': compliance_report.total_actions,
            'policy_evaluations': compliance_report.policy_evaluations,
            'violations': len(compliance_report.violations),
            'compliance_rate': compliance_report.compliance_rate
        }
        
        results['overall_success'] = all(
            phase.get('success', True) 
            for phase in results['phases'].values()
        )
        
        return results
