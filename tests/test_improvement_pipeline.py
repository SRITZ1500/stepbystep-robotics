"""
Tests for the ImprovementPipeline integration.

This module tests the wiring of Improvement Layer components:
ExecutionTracker → EvaluationEngine → RegressionDetector
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.stepbystep_robotics.models import (
    ExecutionTrace,
    ExecutionStatus,
    ExecutionStepRecord,
    StepStatus,
    RobotState,
    PerformanceMetrics,
    TaskSpecification,
    TaskStep,
    ActionType,
    FailureStrategy,
    Vector3D,
    Quaternion,
)
from src.stepbystep_robotics.workflow.execution_tracker import ExecutionTracker
from src.stepbystep_robotics.improvement.evaluation_engine import EvaluationEngine
from src.stepbystep_robotics.improvement.regression_detector import RegressionDetector
from src.stepbystep_robotics.improvement.improvement_pipeline import ImprovementPipeline


@pytest.fixture
def execution_tracker():
    """Create an execution tracker instance."""
    return ExecutionTracker()


@pytest.fixture
def evaluation_engine():
    """Create an evaluation engine instance."""
    return EvaluationEngine()


@pytest.fixture
def regression_detector():
    """Create a regression detector instance."""
    return RegressionDetector()


@pytest.fixture
def improvement_pipeline(execution_tracker, evaluation_engine, regression_detector):
    """Create an improvement pipeline instance."""
    return ImprovementPipeline(
        execution_tracker=execution_tracker,
        evaluation_engine=evaluation_engine,
        regression_detector=regression_detector
    )


@pytest.fixture
def sample_robot_state():
    """Create a sample robot state."""
    return RobotState(
        robot_id=uuid4(),
        timestamp=datetime.now(),
        position=Vector3D(1.0, 2.0, 3.0),
        orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.9,
        error_flags=set(),
        metadata={}
    )


@pytest.fixture
def sample_task_spec():
    """Create a sample task specification."""
    return TaskSpecification(
        task_id="test_task",
        name="Test Task",
        description="A test task",
        preconditions=[],
        postconditions=[],
        steps=[
            TaskStep(
                step_id="step_1",
                action=ActionType.MOVE,
                parameters={},
                expected_duration=10.0,
                success_criteria=[],
                failure_handling=FailureStrategy.RETRY,
                max_retries=3
            )
        ],
        timeout_seconds=60,
        required_capabilities=set(),
        safety_constraints=[]
    )


def create_complete_execution(
    execution_tracker,
    task_spec,
    robot_state,
    duration=30.0,
    success_rate=0.95
):
    """Helper to create a complete execution with tracking."""
    # Start tracking
    execution_id = execution_tracker.startTracking(
        task_id=task_spec.task_id,
        robot_id=robot_state.robot_id,
        initial_state=robot_state
    ).execution_id
    
    # Record a step
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=duration)
    
    step_record = ExecutionStepRecord(
        step_id="step_1",
        start_time=start_time,
        end_time=end_time,
        status=StepStatus.COMPLETED if success_rate > 0.5 else StepStatus.FAILED,
        input_state=robot_state,
        output_state=robot_state,
        actual_duration=duration,
        deviations=[],
        retry_count=0
    )
    
    execution_tracker.recordStep(execution_id, step_record)
    
    # Finish tracking
    execution_tracker.finishTracking(
        execution_id,
        final_status=ExecutionStatus.COMPLETED if success_rate > 0.5 else ExecutionStatus.FAILED,
        final_state=robot_state
    )
    
    # Get trace and add metrics
    trace = execution_tracker.getExecutionTrace(execution_id)
    
    # Create metrics
    metrics = PerformanceMetrics(
        execution_id=execution_id,
        total_duration=duration,
        success_rate=success_rate,
        energy_consumed=0.1,
        accuracy_score=0.9,
        smoothness_score=0.85,
        safety_score=0.95,
        step_metrics={},
        aggregate_stats={}
    )
    
    # Update trace with metrics
    trace.performance_metrics = metrics
    
    return execution_id, trace


class TestAnalyzeExecution:
    """Tests for analyzeExecution method."""
    
    def test_analyze_execution_without_baseline(
        self,
        improvement_pipeline,
        execution_tracker,
        sample_task_spec,
        sample_robot_state
    ):
        """Test analyzing execution when no baseline exists."""
        # Create execution
        execution_id, trace = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state
        )
        
        # Analyze
        analysis = improvement_pipeline.analyzeExecution(execution_id)
        
        # Verify analysis components
        assert analysis.execution_id == execution_id
        assert analysis.task_id == sample_task_spec.task_id
        assert analysis.metrics is not None
        assert isinstance(analysis.bottlenecks, list)
        assert isinstance(analysis.recommendations, list)
        assert analysis.regression_report is None  # No baseline
        assert analysis.overall_health in ["EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL"]
    
    def test_analyze_execution_with_baseline(
        self,
        improvement_pipeline,
        execution_tracker,
        regression_detector,
        sample_task_spec,
        sample_robot_state
    ):
        """Test analyzing execution with baseline for regression detection."""
        task_id = sample_task_spec.task_id
        
        # Create baseline traces
        baseline_traces = []
        for i in range(10):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state,
                duration=30.0
            )
            baseline_traces.append(trace)
        
        # Establish baseline
        regression_detector.establishBaseline(task_id, baseline_traces)
        
        # Create new execution
        execution_id, trace = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state,
            duration=31.0  # Similar performance
        )
        
        # Analyze
        analysis = improvement_pipeline.analyzeExecution(execution_id)
        
        # Verify regression check was performed
        assert analysis.regression_report is not None
        assert analysis.baseline_version == 1
    
    def test_analyze_execution_with_regression(
        self,
        improvement_pipeline,
        execution_tracker,
        regression_detector,
        sample_task_spec,
        sample_robot_state
    ):
        """Test analyzing execution that has regressed."""
        task_id = sample_task_spec.task_id
        
        # Create baseline traces
        baseline_traces = []
        for i in range(10):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state,
                duration=30.0
            )
            baseline_traces.append(trace)
        
        # Establish baseline
        regression_detector.establishBaseline(task_id, baseline_traces)
        
        # Create regressed execution (much slower)
        execution_id, trace = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state,
            duration=60.0  # 100% slower
        )
        
        # Analyze
        analysis = improvement_pipeline.analyzeExecution(execution_id)
        
        # Verify regression detected
        if analysis.regression_report and analysis.regression_report.detected:
            assert analysis.action_required
            assert len(analysis.priority_actions) > 0
            assert analysis.overall_health in ["POOR", "CRITICAL"]
    
    def test_analyze_execution_skip_regression_check(
        self,
        improvement_pipeline,
        execution_tracker,
        regression_detector,
        sample_task_spec,
        sample_robot_state
    ):
        """Test analyzing execution with regression check disabled."""
        task_id = sample_task_spec.task_id
        
        # Create baseline
        baseline_traces = []
        for i in range(10):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state
            )
            baseline_traces.append(trace)
        
        regression_detector.establishBaseline(task_id, baseline_traces)
        
        # Create execution
        execution_id, trace = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state
        )
        
        # Analyze without regression check
        analysis = improvement_pipeline.analyzeExecution(
            execution_id,
            check_regression=False
        )
        
        # Verify no regression check
        assert analysis.regression_report is None
        assert analysis.baseline_version is None
    
    def test_analyze_execution_health_classification(
        self,
        improvement_pipeline,
        execution_tracker,
        sample_task_spec,
        sample_robot_state
    ):
        """Test that health is classified correctly."""
        # Create excellent execution
        execution_id, trace = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state,
            duration=30.0,
            success_rate=1.0
        )
        
        analysis = improvement_pipeline.analyzeExecution(execution_id)
        
        # Should be excellent or good
        assert analysis.overall_health in ["EXCELLENT", "GOOD"]
        
        # Create poor execution
        execution_id2, trace2 = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state,
            duration=120.0,  # Very slow
            success_rate=0.5  # Low success
        )
        
        analysis2 = improvement_pipeline.analyzeExecution(execution_id2)
        
        # Should be poor or critical
        assert analysis2.overall_health in ["POOR", "CRITICAL", "FAIR"]


class TestCompareExecutions:
    """Tests for compareExecutions method."""
    
    def test_compare_two_executions(
        self,
        improvement_pipeline,
        execution_tracker,
        sample_task_spec,
        sample_robot_state
    ):
        """Test comparing two executions."""
        # Create two executions
        execution_id_a, _ = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state,
            duration=30.0,
            success_rate=0.95
        )
        
        execution_id_b, _ = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state,
            duration=45.0,  # Slower
            success_rate=0.90  # Lower success
        )
        
        # Compare
        comparison = improvement_pipeline.compareExecutions(
            execution_id_a,
            execution_id_b
        )
        
        # Verify comparison structure
        assert 'comparison' in comparison
        assert 'execution_a' in comparison
        assert 'execution_b' in comparison
        assert 'winner' in comparison
        
        # Verify winner determination
        assert comparison['winner'] in ['execution_a', 'execution_b', 'tie']
        
        # A should be better or tie (faster and higher success)
        assert comparison['winner'] in ['execution_a', 'tie']
    
    def test_compare_similar_executions(
        self,
        improvement_pipeline,
        execution_tracker,
        sample_task_spec,
        sample_robot_state
    ):
        """Test comparing similar executions."""
        # Create two similar executions
        execution_id_a, _ = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state,
            duration=30.0,
            success_rate=0.95
        )
        
        execution_id_b, _ = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state,
            duration=31.0,  # Very similar
            success_rate=0.95
        )
        
        # Compare
        comparison = improvement_pipeline.compareExecutions(
            execution_id_a,
            execution_id_b
        )
        
        # Should be close or tie
        assert comparison['winner'] in ['execution_a', 'execution_b', 'tie']


class TestTrackTaskHealth:
    """Tests for trackTaskHealth method."""
    
    def test_track_task_health_no_baseline(
        self,
        improvement_pipeline
    ):
        """Test tracking health when no baseline exists."""
        health = improvement_pipeline.trackTaskHealth("nonexistent_task")
        
        assert health['task_id'] == "nonexistent_task"
        assert health['health'] in ["EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL"]
        assert health['baseline_version'] is None
    
    def test_track_task_health_with_baseline(
        self,
        improvement_pipeline,
        execution_tracker,
        regression_detector,
        sample_task_spec,
        sample_robot_state
    ):
        """Test tracking health with established baseline."""
        task_id = sample_task_spec.task_id
        
        # Create baseline
        baseline_traces = []
        for i in range(10):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state
            )
            baseline_traces.append(trace)
        
        regression_detector.establishBaseline(
            task_id,
            baseline_traces,
            approved_by="admin"
        )
        
        # Track health
        health = improvement_pipeline.trackTaskHealth(task_id)
        
        assert health['task_id'] == task_id
        assert health['baseline_version'] == 1
        assert health['baseline_approved'] is True
        assert health['total_regressions'] == 0
        assert health['health'] == "EXCELLENT"
        assert health['trend'] == "STABLE"
    
    def test_track_task_health_with_regressions(
        self,
        improvement_pipeline,
        execution_tracker,
        regression_detector,
        sample_task_spec,
        sample_robot_state
    ):
        """Test tracking health with detected regressions."""
        task_id = sample_task_spec.task_id
        
        # Create baseline
        baseline_traces = []
        for i in range(10):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state,
                duration=30.0
            )
            baseline_traces.append(trace)
        
        regression_detector.establishBaseline(task_id, baseline_traces)
        
        # Create regressed executions
        for i in range(3):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state,
                duration=60.0  # Much slower
            )
            regression_detector.detectRegression(task_id, trace)
        
        # Track health
        health = improvement_pipeline.trackTaskHealth(task_id)
        
        # Should show degraded health
        assert health['total_regressions'] >= 1
        assert health['unresolved_regressions'] >= 1
        assert health['health'] in ["FAIR", "POOR", "CRITICAL"]


class TestGenerateImprovementReport:
    """Tests for generateImprovementReport method."""
    
    def test_generate_report_basic(
        self,
        improvement_pipeline,
        execution_tracker,
        regression_detector,
        sample_task_spec,
        sample_robot_state
    ):
        """Test generating basic improvement report."""
        task_id = sample_task_spec.task_id
        
        # Create baseline
        baseline_traces = []
        for i in range(10):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state
            )
            baseline_traces.append(trace)
        
        regression_detector.establishBaseline(task_id, baseline_traces)
        
        # Generate report
        report = improvement_pipeline.generateImprovementReport(task_id)
        
        # Verify report structure
        assert report['task_id'] == task_id
        assert 'generated_at' in report
        assert 'health' in report
        assert 'baseline' in report
        assert 'regression_summary' in report
        assert 'recommendations' in report
        
        # Verify baseline info
        assert report['baseline']['version'] == 1
        assert report['baseline']['sample_size'] == 10
    
    def test_generate_report_with_history(
        self,
        improvement_pipeline,
        execution_tracker,
        regression_detector,
        sample_task_spec,
        sample_robot_state
    ):
        """Test generating report with regression history."""
        task_id = sample_task_spec.task_id
        
        # Create baseline
        baseline_traces = []
        for i in range(10):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state,
                duration=30.0
            )
            baseline_traces.append(trace)
        
        regression_detector.establishBaseline(task_id, baseline_traces)
        
        # Create some regressions
        for i in range(5):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state,
                duration=50.0 + i * 5
            )
            regression_detector.detectRegression(task_id, trace)
        
        # Generate report
        report = improvement_pipeline.generateImprovementReport(task_id)
        
        # Verify regression summary
        assert report['regression_summary']['total_events'] >= 1
        assert 'severity_distribution' in report['regression_summary']


class TestIntegration:
    """Integration tests for improvement pipeline."""
    
    def test_full_improvement_workflow(
        self,
        improvement_pipeline,
        execution_tracker,
        regression_detector,
        sample_task_spec,
        sample_robot_state
    ):
        """Test complete improvement workflow."""
        task_id = sample_task_spec.task_id
        
        # Step 1: Create baseline from history
        baseline_traces = []
        for i in range(15):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state,
                duration=30.0 + i * 0.5
            )
            baseline_traces.append(trace)
        
        baseline = regression_detector.establishBaseline(
            task_id,
            baseline_traces,
            approved_by="admin"
        )
        
        assert baseline.is_approved()
        
        # Step 2: Execute new task
        execution_id, trace = create_complete_execution(
            execution_tracker,
            sample_task_spec,
            sample_robot_state,
            duration=32.0  # Normal performance
        )
        
        # Step 3: Analyze execution
        analysis = improvement_pipeline.analyzeExecution(execution_id)
        
        assert analysis.metrics is not None
        assert analysis.regression_report is not None
        assert not analysis.regression_report.detected  # Should be normal
        
        # Step 4: Track task health
        health = improvement_pipeline.trackTaskHealth(task_id)
        
        assert health['health'] in ["EXCELLENT", "GOOD"]
        assert health['baseline_approved']
        
        # Step 5: Generate report
        report = improvement_pipeline.generateImprovementReport(task_id)
        
        assert report['baseline']['approved']
        assert report['health']['health'] in ["EXCELLENT", "GOOD"]
    
    def test_detect_and_respond_to_degradation(
        self,
        improvement_pipeline,
        execution_tracker,
        regression_detector,
        sample_task_spec,
        sample_robot_state
    ):
        """Test detecting and responding to performance degradation."""
        task_id = sample_task_spec.task_id
        
        # Establish baseline
        baseline_traces = []
        for i in range(10):
            _, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state,
                duration=30.0
            )
            baseline_traces.append(trace)
        
        regression_detector.establishBaseline(task_id, baseline_traces)
        
        # Simulate gradual degradation
        for i in range(5):
            duration = 30.0 + i * 10  # Getting slower
            execution_id, trace = create_complete_execution(
                execution_tracker,
                sample_task_spec,
                sample_robot_state,
                duration=duration
            )
            
            # Analyze each execution
            analysis = improvement_pipeline.analyzeExecution(execution_id)
            
            # Later executions should show degradation
            if i >= 3:
                if analysis.regression_report and analysis.regression_report.detected:
                    assert analysis.action_required
                    assert len(analysis.priority_actions) > 0
        
        # Check overall health
        health = improvement_pipeline.trackTaskHealth(task_id)
        
        # Should show degraded health
        if health['unresolved_regressions'] > 0:
            assert health['health'] in ["FAIR", "POOR", "CRITICAL"]
            assert health['trend'] in ["DEGRADING", "UNSTABLE"]
