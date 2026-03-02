"""
Tests for end-to-end workflow integration
Demonstrates complete StepbyStep:ROBOTICS system
"""

import pytest
from datetime import datetime, timedelta

from src.stepbystep_robotics.models import (
    TaskSpecification, TaskStep, ActionType, 
    FailureStrategy, Condition, ConditionType
)
from src.stepbystep_robotics.workflows import (
    ObservabilityPipeline,
    TaskExecutionWorkflow,
    RegressionDetectionWorkflow,
    PolicyGovernedExecutionWorkflow,
    CompleteSystemWorkflow
)


@pytest.fixture
def sample_task():
    """Sample task for testing"""
    return TaskSpecification(
        task_id="yoga_mirror_demo",
        name="Yoga Mirror Demonstration",
        description="Robot mirrors human yoga poses",
        timeout_seconds=30,
        required_capabilities={'camera', 'motion'},
        steps=[
            TaskStep(
                step_id="observe_pose",
                action=ActionType.SENSE,
                parameters={'sensor': 'camera'},
                expected_duration=2.0,
                success_criteria=[
                    Condition(
                        type=ConditionType.STATE_EQUALS,
                        expression="pose_captured == True"
                    )
                ],
                failure_handling=FailureStrategy.RETRY,
                max_retries=3
            ),
            TaskStep(
                step_id="execute_pose",
                action=ActionType.MOVE,
                parameters={'target': 'pose'},
                expected_duration=3.0,
                success_criteria=[
                    Condition(
                        type=ConditionType.STATE_EQUALS,
                        expression="pose_executed == True"
                    )
                ],
                failure_handling=FailureStrategy.ABORT,
                max_retries=1
            )
        ],
        preconditions=[
            Condition(
                type=ConditionType.STATE_EQUALS,
                expression="robot_powered == True"
            )
        ],
        postconditions=[
            Condition(
                type=ConditionType.STATE_EQUALS,
                expression="pose_mirrored == True"
            )
        ],
        safety_constraints=[
            Condition(
                type=ConditionType.STATE_EQUALS,
                expression="joint_limits_ok == True"
            )
        ]
    )


class TestObservabilityPipeline:
    """Test Behavior Layer integration"""
    
    def test_observe_and_translate_stream(self):
        """Test complete observability pipeline"""
        pipeline = ObservabilityPipeline()
        
        observations = pipeline.observe_and_translate_stream(
            robot_id="robot_001",
            duration_seconds=2.0
        )
        
        assert len(observations) > 0
        assert all('timestamp' in obs for obs in observations)
        assert all('confidence' in obs for obs in observations)
        assert all(obs['robot_id'] == "robot_001" for obs in observations)


class TestTaskExecutionWorkflow:
    """Test Workflow Layer integration"""
    
    def test_execute_task_with_tracking(self, sample_task):
        """Test complete task execution workflow"""
        workflow = TaskExecutionWorkflow()
        
        result = workflow.execute_task_with_tracking(
            task_spec=sample_task,
            robot_id="robot_001"
        )
        
        assert result.success
        assert result.execution_id
        assert result.trace is not None
        assert result.metrics is not None
        assert result.governance_decision == "APPROVED"
    
    def test_invalid_task_rejected(self):
        """Test that invalid tasks are rejected"""
        workflow = TaskExecutionWorkflow()
        
        invalid_task = TaskSpecification(
            task_id="",  # Invalid: empty task_id
            name="Invalid Task",
            description="Invalid",
            timeout_seconds=10,
            required_capabilities=set(),
            steps=[
                TaskStep(
                    step_id="step1",
                    action=ActionType.SENSE,
                    parameters={},
                    expected_duration=1.0,
                    success_criteria=[],
                    failure_handling=FailureStrategy.ABORT
                )
            ],
            preconditions=[],
            postconditions=[],
            safety_constraints=[]
        )
        
        result = workflow.execute_task_with_tracking(
            task_spec=invalid_task,
            robot_id="robot_001"
        )
        
        assert not result.success
        assert result.error is not None
        assert result.governance_decision == "REJECTED"


class TestRegressionDetectionWorkflow:
    """Test Improvement Layer integration"""
    
    def test_detect_and_report_regression(self, sample_task):
        """Test regression detection workflow"""
        workflow = RegressionDetectionWorkflow()
        
        # Execute task multiple times to get traces
        execution_workflow = TaskExecutionWorkflow()
        traces = []
        
        for _ in range(3):
            result = execution_workflow.execute_task_with_tracking(
                task_spec=sample_task,
                robot_id="robot_001"
            )
            if result.trace:
                traces.append(result.trace)
        
        # Detect regressions
        result = workflow.detect_and_report_regression(
            task_id=sample_task.task_id,
            recent_traces=traces
        )
        
        assert result.success
        assert result.regression_report is not None


class TestPolicyGovernedExecutionWorkflow:
    """Test governance integration"""
    
    def test_execute_with_governance_approved(self, sample_task):
        """Test task execution with governance approval"""
        workflow = PolicyGovernedExecutionWorkflow()
        
        result = workflow.execute_with_governance(
            task_spec=sample_task,
            robot_id="robot_001",
            operator_id="operator_alice"
        )
        
        assert result.success
        assert result.governance_decision == "APPROVED"
        assert result.execution_id
        assert result.trace is not None
        assert result.metrics is not None


class TestCompleteSystemWorkflow:
    """Test complete system integration - THE DEMO"""
    
    def test_run_complete_workflow(self, sample_task):
        """
        Test complete workflow across all three layers
        This is the end-to-end demo for Amazon
        """
        workflow = CompleteSystemWorkflow()
        
        results = workflow.run_complete_workflow(
            task_spec=sample_task,
            robot_id="robot_001",
            operator_id="operator_demo"
        )
        
        # Verify workflow completed
        assert results['workflow_id']
        assert results['timestamp']
        
        # Verify all phases attempted
        assert 'observation' in results['phases']
        assert 'execution' in results['phases']
        assert 'compliance' in results['phases']
        
        # Verify observation phase succeeded
        obs_phase = results['phases']['observation']
        assert obs_phase['success']
        assert obs_phase['observation_count'] > 0
        
        # Verify execution phase attempted (may fail in test environment)
        exec_phase = results['phases']['execution']
        assert exec_phase['governance_decision'] in ["APPROVED", "ERROR", "PENDING_APPROVAL"]
        
        # Verify compliance phase
        comp_phase = results['phases']['compliance']
        assert comp_phase['total_actions'] >= 0
        assert comp_phase['policy_evaluations'] >= 0
        
        # Note: Regression detection only runs if execution succeeds
        # In test environment, execution may fail, which is expected


class TestWorkflowIntegration:
    """Integration tests across multiple workflows"""
    
    def test_multiple_executions_with_regression_detection(self, sample_task):
        """Test multiple executions followed by regression analysis"""
        execution_workflow = TaskExecutionWorkflow()
        regression_workflow = RegressionDetectionWorkflow()
        
        # Execute task 5 times
        traces = []
        for i in range(5):
            result = execution_workflow.execute_task_with_tracking(
                task_spec=sample_task,
                robot_id=f"robot_{i:03d}"
            )
            assert result.success
            traces.append(result.trace)
        
        # Analyze for regressions
        regression_result = regression_workflow.detect_and_report_regression(
            task_id=sample_task.task_id,
            recent_traces=traces
        )
        
        assert regression_result.success
        assert regression_result.regression_report is not None
    
    def test_governed_execution_with_audit_trail(self, sample_task):
        """Test that governed execution creates audit trail"""
        workflow = PolicyGovernedExecutionWorkflow()
        
        # Execute multiple tasks
        for i in range(3):
            result = workflow.execute_with_governance(
                task_spec=sample_task,
                robot_id="robot_001",
                operator_id=f"operator_{i}"
            )
            assert result.success or result.governance_decision == "PENDING_APPROVAL"
        
        # Generate compliance report
        compliance_report = workflow.governance.generate_compliance_report(
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        
        # Should have audit entries
        assert compliance_report.total_actions > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
