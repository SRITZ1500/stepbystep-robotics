"""
Tests for the EvaluationEngine component.

This module tests the evaluation engine's ability to compute metrics,
compare executions, identify bottlenecks, and generate recommendations.
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
    Anomaly,
    Deviation,
    Vector3D,
    Quaternion,
)
from src.stepbystep_robotics.improvement.evaluation_engine import (
    EvaluationEngine,
    BottleneckInfo,
    Recommendation,
    ComparisonReport,
)


@pytest.fixture
def evaluation_engine():
    """Create an evaluation engine instance."""
    return EvaluationEngine()


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
        battery_level=0.8,
        error_flags=set(),
        metadata={}
    )


@pytest.fixture
def successful_trace(sample_robot_state):
    """Create a successful execution trace."""
    start_time = datetime.now()
    
    steps = []
    for i in range(3):
        step_start = start_time + timedelta(seconds=i * 10)
        step_end = step_start + timedelta(seconds=8)
        
        steps.append(ExecutionStepRecord(
            step_id=f"step_{i}",
            start_time=step_start,
            end_time=step_end,
            status=StepStatus.COMPLETED,
            input_state=sample_robot_state,
            output_state=sample_robot_state,
            actual_duration=8.0,
            deviations=[],
            retry_count=0
        ))
    
    end_time = start_time + timedelta(seconds=30)
    
    # Create state history with battery drain
    initial_state = RobotState(
        robot_id=sample_robot_state.robot_id,
        timestamp=start_time,
        position=Vector3D(1.0, 2.0, 3.0),
        orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=1.0,
        error_flags=set(),
        metadata={}
    )
    
    final_state = RobotState(
        robot_id=sample_robot_state.robot_id,
        timestamp=end_time,
        position=Vector3D(1.0, 2.0, 3.0),
        orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.85,
        error_flags=set(),
        metadata={}
    )
    
    return ExecutionTrace(
        execution_id=str(uuid4()),
        task_id="test_task",
        robot_id=sample_robot_state.robot_id,
        start_time=start_time,
        end_time=end_time,
        status=ExecutionStatus.COMPLETED,
        steps=steps,
        state_history=[initial_state, final_state],
        anomalies=[],
        performance_metrics=None
    )


@pytest.fixture
def problematic_trace(sample_robot_state):
    """Create a trace with various issues."""
    start_time = datetime.now()
    
    steps = []
    
    # Step 0: Slow step
    steps.append(ExecutionStepRecord(
        step_id="step_0",
        start_time=start_time,
        end_time=start_time + timedelta(seconds=30),
        status=StepStatus.COMPLETED,
        input_state=sample_robot_state,
        output_state=sample_robot_state,
        actual_duration=30.0,
        deviations=[],
        retry_count=0
    ))
    
    # Step 1: High retry step
    steps.append(ExecutionStepRecord(
        step_id="step_1",
        start_time=start_time + timedelta(seconds=30),
        end_time=start_time + timedelta(seconds=40),
        status=StepStatus.COMPLETED,
        input_state=sample_robot_state,
        output_state=sample_robot_state,
        actual_duration=10.0,
        deviations=[],
        retry_count=5
    ))
    
    # Step 2: High deviation step
    deviations = [
        Deviation(
            metric="POSITION",
            expected=1.0,
            actual=1.5,
            severity="HIGH"
        )
        for i in range(6)
    ]
    
    steps.append(ExecutionStepRecord(
        step_id="step_2",
        start_time=start_time + timedelta(seconds=40),
        end_time=start_time + timedelta(seconds=50),
        status=StepStatus.COMPLETED,
        input_state=sample_robot_state,
        output_state=sample_robot_state,
        actual_duration=10.0,
        deviations=deviations,
        retry_count=0
    ))
    
    # Step 3: Failed step
    steps.append(ExecutionStepRecord(
        step_id="step_3",
        start_time=start_time + timedelta(seconds=50),
        end_time=start_time + timedelta(seconds=55),
        status=StepStatus.FAILED,
        input_state=sample_robot_state,
        output_state=sample_robot_state,
        actual_duration=5.0,
        deviations=[],
        retry_count=3
    ))
    
    end_time = start_time + timedelta(seconds=55)
    
    # Add anomalies
    anomalies = [
        Anomaly(
            timestamp=start_time + timedelta(seconds=45),
            anomaly_type="TIMING_VIOLATION",
            severity="CRITICAL",
            description="Step exceeded expected duration",
            context={}
        ),
        Anomaly(
            timestamp=start_time + timedelta(seconds=52),
            anomaly_type="EXECUTION_FAILURE",
            severity="WARNING",
            description="Step failed after retries",
            context={}
        )
    ]
    
    # State history with high battery drain
    initial_state = RobotState(
        robot_id=sample_robot_state.robot_id,
        timestamp=start_time,
        position=Vector3D(1.0, 2.0, 3.0),
        orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=1.0,
        error_flags=set(),
        metadata={}
    )
    
    final_state = RobotState(
        robot_id=sample_robot_state.robot_id,
        timestamp=end_time,
        position=Vector3D(1.0, 2.0, 3.0),
        orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        joint_states={},
        sensor_readings={},
        actuator_states={},
        battery_level=0.6,
        error_flags=set(),
        metadata={}
    )
    
    return ExecutionTrace(
        execution_id=str(uuid4()),
        task_id="test_task",
        robot_id=sample_robot_state.robot_id,
        start_time=start_time,
        end_time=end_time,
        status=ExecutionStatus.FAILED,
        steps=steps,
        state_history=[initial_state, final_state],
        anomalies=anomalies,
        performance_metrics=None
    )


class TestEvaluateExecution:
    """Tests for evaluateExecution method."""
    
    def test_compute_metrics_for_successful_trace(self, evaluation_engine, successful_trace):
        """Test computing metrics for a successful execution."""
        metrics = evaluation_engine.evaluateExecution(successful_trace)
        
        # Verify basic metrics
        assert metrics.execution_id == successful_trace.execution_id
        assert metrics.total_duration == 30.0
        assert metrics.success_rate == 1.0  # All steps completed
        assert 0.0 <= metrics.energy_consumed <= 1.0
        
        # Verify score ranges (Requirement 7.4, 17.3)
        assert 0.0 <= metrics.accuracy_score <= 1.0
        assert 0.0 <= metrics.smoothness_score <= 1.0
        assert 0.0 <= metrics.safety_score <= 1.0
        
        # Verify energy is non-negative (Requirement 7.5, 17.4)
        assert metrics.energy_consumed >= 0.0
        
        # Verify step metrics exist for all steps (Requirement 17.5)
        assert len(metrics.step_metrics) == len(successful_trace.steps)
        for step in successful_trace.steps:
            assert step.step_id in metrics.step_metrics
    
    def test_compute_metrics_for_problematic_trace(self, evaluation_engine, problematic_trace):
        """Test computing metrics for a problematic execution."""
        metrics = evaluation_engine.evaluateExecution(problematic_trace)
        
        # Verify success rate reflects failures (Requirement 7.3, 17.2)
        expected_success_rate = 3 / 4  # 3 completed out of 4 total
        assert metrics.success_rate == expected_success_rate
        
        # Verify accuracy score is lower due to deviations
        assert metrics.accuracy_score < 0.8
        
        # Verify safety score is lower due to anomalies
        assert metrics.safety_score < 1.0
        
        # Verify energy consumed is higher
        assert metrics.energy_consumed > 0.3
    
    def test_total_duration_calculation(self, evaluation_engine, successful_trace):
        """Test that total duration equals end_time - start_time (Requirement 7.2, 17.1)."""
        metrics = evaluation_engine.evaluateExecution(successful_trace)
        
        expected_duration = (
            successful_trace.end_time - successful_trace.start_time
        ).total_seconds()
        
        assert metrics.total_duration == expected_duration
    
    def test_success_rate_calculation(self, evaluation_engine, problematic_trace):
        """Test that success rate equals successful_steps / total_steps (Requirement 17.2)."""
        metrics = evaluation_engine.evaluateExecution(problematic_trace)
        
        successful_count = sum(
            1 for step in problematic_trace.steps
            if step.status == StepStatus.COMPLETED
        )
        total_count = len(problematic_trace.steps)
        expected_rate = successful_count / total_count
        
        assert metrics.success_rate == expected_rate
    
    def test_energy_consumed_non_negative(self, evaluation_engine, successful_trace):
        """Test that energy consumed is always non-negative (Requirement 7.5, 17.4)."""
        metrics = evaluation_engine.evaluateExecution(successful_trace)
        
        assert metrics.energy_consumed >= 0.0
    
    def test_empty_trace_handling(self, evaluation_engine, sample_robot_state):
        """Test handling of trace with no steps."""
        empty_trace = ExecutionTrace(
            execution_id=str(uuid4()),
            task_id="empty_task",
            robot_id=sample_robot_state.robot_id,
            start_time=datetime.now(),
            end_time=datetime.now(),
            status=ExecutionStatus.COMPLETED,
            steps=[],
            state_history=[sample_robot_state],
            anomalies=[],
            performance_metrics=None
        )
        
        metrics = evaluation_engine.evaluateExecution(empty_trace)
        
        assert metrics.success_rate == 0.0
        assert metrics.accuracy_score == 1.0  # No deviations
        assert len(metrics.step_metrics) == 0


class TestCompareExecutions:
    """Tests for compareExecutions method."""
    
    def test_compare_similar_executions(self, evaluation_engine, successful_trace):
        """Test comparing two similar executions."""
        # Create a second similar trace
        trace_b = ExecutionTrace(
            execution_id=str(uuid4()),
            task_id=successful_trace.task_id,
            robot_id=successful_trace.robot_id,
            start_time=successful_trace.start_time,
            end_time=successful_trace.end_time + timedelta(seconds=2),
            status=ExecutionStatus.COMPLETED,
            steps=successful_trace.steps,
            state_history=successful_trace.state_history,
            anomalies=[],
            performance_metrics=None
        )
        
        report = evaluation_engine.compareExecutions(successful_trace, trace_b)
        
        assert report.execution_a_id == successful_trace.execution_id
        assert report.execution_b_id == trace_b.execution_id
        assert abs(report.duration_delta) < 5.0  # Small difference
        assert "similar" in report.summary.lower()
    
    def test_compare_different_executions(self, evaluation_engine, successful_trace, problematic_trace):
        """Test comparing executions with significant differences."""
        report = evaluation_engine.compareExecutions(successful_trace, problematic_trace)
        
        # Verify deltas are computed
        assert report.duration_delta != 0.0
        assert report.success_rate_delta != 0.0
        
        # Verify summary highlights differences
        assert len(report.summary) > 0
    
    def test_step_by_step_comparison(self, evaluation_engine, successful_trace):
        """Test that step-by-step comparisons are included."""
        # Create trace with same steps but different durations
        modified_steps = []
        for step in successful_trace.steps:
            modified_step = ExecutionStepRecord(
                step_id=step.step_id,
                start_time=step.start_time,
                end_time=step.end_time + timedelta(seconds=2),
                status=step.status,
                input_state=step.input_state,
                output_state=step.output_state,
                actual_duration=step.actual_duration + 2.0,
                deviations=step.deviations,
                retry_count=step.retry_count
            )
            modified_steps.append(modified_step)
        
        trace_b = ExecutionTrace(
            execution_id=str(uuid4()),
            task_id=successful_trace.task_id,
            robot_id=successful_trace.robot_id,
            start_time=successful_trace.start_time,
            end_time=successful_trace.end_time + timedelta(seconds=6),
            status=ExecutionStatus.COMPLETED,
            steps=modified_steps,
            state_history=successful_trace.state_history,
            anomalies=[],
            performance_metrics=None
        )
        
        report = evaluation_engine.compareExecutions(successful_trace, trace_b)
        
        # Verify step comparisons exist
        assert len(report.step_comparisons) > 0
        for step_id in report.step_comparisons:
            assert 'duration_delta' in report.step_comparisons[step_id]


class TestIdentifyBottlenecks:
    """Tests for identifyBottlenecks method."""
    
    def test_identify_slow_steps(self, evaluation_engine, problematic_trace):
        """Test identification of slow steps."""
        bottlenecks = evaluation_engine.identifyBottlenecks(problematic_trace)
        
        # Should identify step_0 as slow (30s vs avg ~14s)
        slow_bottlenecks = [b for b in bottlenecks if b.issue_type == "SLOW"]
        assert len(slow_bottlenecks) > 0
        
        # Verify bottleneck info
        slow_step = slow_bottlenecks[0]
        assert slow_step.step_id == "step_0"
        assert slow_step.severity in ["HIGH", "CRITICAL"]
    
    def test_identify_high_retry_steps(self, evaluation_engine, problematic_trace):
        """Test identification of steps with high retry counts."""
        bottlenecks = evaluation_engine.identifyBottlenecks(problematic_trace)
        
        # Should identify step_1 with 5 retries
        retry_bottlenecks = [b for b in bottlenecks if b.issue_type == "HIGH_RETRY"]
        assert len(retry_bottlenecks) > 0
        
        retry_step = retry_bottlenecks[0]
        assert retry_step.step_id == "step_1"
        assert retry_step.metric_value == 5.0
    
    def test_identify_high_deviation_steps(self, evaluation_engine, problematic_trace):
        """Test identification of steps with high deviations."""
        bottlenecks = evaluation_engine.identifyBottlenecks(problematic_trace)
        
        # Should identify step_2 with 6 deviations
        deviation_bottlenecks = [b for b in bottlenecks if b.issue_type == "HIGH_DEVIATION"]
        assert len(deviation_bottlenecks) > 0
        
        deviation_step = deviation_bottlenecks[0]
        assert deviation_step.step_id == "step_2"
        assert deviation_step.metric_value == 6.0
    
    def test_bottlenecks_sorted_by_severity(self, evaluation_engine, problematic_trace):
        """Test that bottlenecks are sorted by severity."""
        bottlenecks = evaluation_engine.identifyBottlenecks(problematic_trace)
        
        # Verify sorting (CRITICAL before HIGH before MEDIUM)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        for i in range(len(bottlenecks) - 1):
            current_order = severity_order.get(bottlenecks[i].severity, 4)
            next_order = severity_order.get(bottlenecks[i + 1].severity, 4)
            assert current_order <= next_order
    
    def test_no_bottlenecks_for_good_trace(self, evaluation_engine, successful_trace):
        """Test that good traces have no or few bottlenecks."""
        bottlenecks = evaluation_engine.identifyBottlenecks(successful_trace)
        
        # Should have no critical bottlenecks
        critical = [b for b in bottlenecks if b.severity == "CRITICAL"]
        assert len(critical) == 0


class TestGenerateRecommendations:
    """Tests for generateRecommendations method."""
    
    def test_generate_recommendations_for_good_performance(self, evaluation_engine, successful_trace):
        """Test recommendations for good performance."""
        metrics = evaluation_engine.evaluateExecution(successful_trace)
        recommendations = evaluation_engine.generateRecommendations(metrics)
        
        # Should have few or no critical recommendations
        critical = [r for r in recommendations if r.priority == "CRITICAL"]
        assert len(critical) == 0
    
    def test_generate_recommendations_for_poor_performance(self, evaluation_engine, problematic_trace):
        """Test recommendations for poor performance."""
        metrics = evaluation_engine.evaluateExecution(problematic_trace)
        recommendations = evaluation_engine.generateRecommendations(metrics, problematic_trace)
        
        # Should have multiple recommendations
        assert len(recommendations) > 0
        
        # Should have high priority recommendations
        high_priority = [r for r in recommendations if r.priority in ["HIGH", "CRITICAL"]]
        assert len(high_priority) > 0
    
    def test_recommendations_sorted_by_priority(self, evaluation_engine, problematic_trace):
        """Test that recommendations are sorted by priority."""
        metrics = evaluation_engine.evaluateExecution(problematic_trace)
        recommendations = evaluation_engine.generateRecommendations(metrics, problematic_trace)
        
        # Verify sorting (CRITICAL before HIGH before MEDIUM before LOW)
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        for i in range(len(recommendations) - 1):
            current_order = priority_order.get(recommendations[i].priority, 4)
            next_order = priority_order.get(recommendations[i + 1].priority, 4)
            assert current_order <= next_order
    
    def test_recommendation_categories(self, evaluation_engine, problematic_trace):
        """Test that recommendations cover different categories."""
        metrics = evaluation_engine.evaluateExecution(problematic_trace)
        recommendations = evaluation_engine.generateRecommendations(metrics, problematic_trace)
        
        categories = {r.category for r in recommendations}
        
        # Should have recommendations in multiple categories
        assert len(categories) > 1
        
        # Common categories should be present
        expected_categories = {"PERFORMANCE", "RELIABILITY", "SAFETY"}
        assert len(categories.intersection(expected_categories)) > 0
    
    def test_recommendations_include_affected_steps(self, evaluation_engine, problematic_trace):
        """Test that recommendations identify affected steps."""
        metrics = evaluation_engine.evaluateExecution(problematic_trace)
        recommendations = evaluation_engine.generateRecommendations(metrics, problematic_trace)
        
        # Some recommendations should have affected steps
        with_steps = [r for r in recommendations if r.affected_steps]
        assert len(with_steps) > 0
    
    def test_low_success_rate_recommendation(self, evaluation_engine, problematic_trace):
        """Test recommendation for low success rate."""
        metrics = evaluation_engine.evaluateExecution(problematic_trace)
        recommendations = evaluation_engine.generateRecommendations(metrics)
        
        # Should recommend improving success rate
        reliability_recs = [r for r in recommendations if r.category == "RELIABILITY"]
        assert len(reliability_recs) > 0
    
    def test_high_energy_recommendation(self, evaluation_engine, problematic_trace):
        """Test recommendation for high energy consumption."""
        metrics = evaluation_engine.evaluateExecution(problematic_trace)
        recommendations = evaluation_engine.generateRecommendations(metrics)
        
        # Should recommend reducing energy consumption
        efficiency_recs = [r for r in recommendations if r.category == "EFFICIENCY"]
        assert len(efficiency_recs) > 0
    
    def test_safety_recommendation(self, evaluation_engine, problematic_trace):
        """Test recommendation for safety issues."""
        metrics = evaluation_engine.evaluateExecution(problematic_trace)
        recommendations = evaluation_engine.generateRecommendations(metrics)
        
        # Should recommend addressing safety concerns
        safety_recs = [r for r in recommendations if r.category == "SAFETY"]
        assert len(safety_recs) > 0


class TestIntegration:
    """Integration tests for the evaluation engine."""
    
    def test_full_evaluation_workflow(self, evaluation_engine, successful_trace, problematic_trace):
        """Test complete evaluation workflow."""
        # Evaluate both traces
        metrics_good = evaluation_engine.evaluateExecution(successful_trace)
        metrics_bad = evaluation_engine.evaluateExecution(problematic_trace)
        
        # Compare them
        comparison = evaluation_engine.compareExecutions(successful_trace, problematic_trace)
        
        # Identify bottlenecks in problematic trace
        bottlenecks = evaluation_engine.identifyBottlenecks(problematic_trace)
        
        # Generate recommendations
        recommendations = evaluation_engine.generateRecommendations(metrics_bad, problematic_trace)
        
        # Verify workflow produces meaningful results
        assert metrics_good.success_rate > metrics_bad.success_rate
        assert comparison.success_rate_delta < 0  # B is worse than A
        assert len(bottlenecks) > 0
        assert len(recommendations) > 0
    
    def test_metrics_validation(self, evaluation_engine, successful_trace):
        """Test that computed metrics pass validation."""
        metrics = evaluation_engine.evaluateExecution(successful_trace)
        
        # Metrics should be valid (no exceptions raised during creation)
        assert metrics.execution_id == successful_trace.execution_id
        
        # All scores should be in valid range
        assert 0.0 <= metrics.success_rate <= 1.0
        assert 0.0 <= metrics.accuracy_score <= 1.0
        assert 0.0 <= metrics.smoothness_score <= 1.0
        assert 0.0 <= metrics.safety_score <= 1.0
        
        # Energy should be non-negative
        assert metrics.energy_consumed >= 0.0
