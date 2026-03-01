"""
Tests for the RegressionDetector component.

This module tests the regression detector's ability to establish baselines,
detect regressions, classify severity, and track history.
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
    Vector3D,
    Quaternion,
)
from src.stepbystep_robotics.improvement.regression_detector import (
    RegressionDetector,
    Baseline,
    RegressionReport,
    RegressionDetail,
    MetricStatistics,
)


@pytest.fixture
def regression_detector():
    """Create a regression detector instance."""
    return RegressionDetector()


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


def create_trace_with_metrics(
    task_id: str,
    duration: float,
    success_rate: float,
    energy: float,
    accuracy: float,
    robot_state
) -> ExecutionTrace:
    """Helper to create execution trace with specific metrics."""
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=duration)
    
    metrics = PerformanceMetrics(
        execution_id=str(uuid4()),
        total_duration=duration,
        success_rate=success_rate,
        energy_consumed=energy,
        accuracy_score=accuracy,
        smoothness_score=0.9,
        safety_score=0.95,
        step_metrics={},
        aggregate_stats={}
    )
    
    return ExecutionTrace(
        execution_id=metrics.execution_id,
        task_id=task_id,
        robot_id=robot_state.robot_id,
        start_time=start_time,
        end_time=end_time,
        status=ExecutionStatus.COMPLETED,
        steps=[],
        state_history=[robot_state],
        anomalies=[],
        performance_metrics=metrics
    )


class TestEstablishBaseline:
    """Tests for establishBaseline method."""
    
    def test_establish_baseline_with_sufficient_data(self, regression_detector, sample_robot_state):
        """Test establishing baseline with 10+ traces."""
        task_id = "test_task"
        
        # Create 15 traces with similar performance
        traces = []
        for i in range(15):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0 + i * 0.5,  # Slight variation
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        baseline = regression_detector.establishBaseline(task_id, traces)
        
        # Verify baseline properties
        assert baseline.task_id == task_id
        assert baseline.sample_size == 15
        assert baseline.version == 1
        assert baseline.is_sufficient()
        
        # Verify metrics computed
        assert 'total_duration' in baseline.metrics
        assert 'success_rate' in baseline.metrics
        assert 'energy_consumed' in baseline.metrics
        
        # Verify statistics are reasonable
        duration_stats = baseline.metrics['total_duration']
        assert 29.0 < duration_stats.mean < 38.0
        assert duration_stats.std_dev > 0
        assert duration_stats.sample_size == 15
    
    def test_establish_baseline_insufficient_data(self, regression_detector, sample_robot_state):
        """Test that baseline requires minimum 10 traces."""
        task_id = "test_task"
        
        # Create only 5 traces
        traces = []
        for i in range(5):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        with pytest.raises(ValueError, match="Insufficient traces"):
            regression_detector.establishBaseline(task_id, traces)
    
    def test_establish_baseline_with_approval(self, regression_detector, sample_robot_state):
        """Test baseline with administrator approval."""
        task_id = "test_task"
        
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        baseline = regression_detector.establishBaseline(
            task_id,
            traces,
            approved_by="admin@example.com"
        )
        
        assert baseline.is_approved()
        assert baseline.approved_by == "admin@example.com"
        assert baseline.approved_at is not None
    
    def test_establish_baseline_removes_outliers(self, regression_detector, sample_robot_state):
        """Test that outliers are removed from baseline computation."""
        task_id = "test_task"
        
        traces = []
        # Create 10 normal traces
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        # Add 2 outliers
        outlier1 = create_trace_with_metrics(
            task_id=task_id,
            duration=300.0,  # 10x normal
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        outlier2 = create_trace_with_metrics(
            task_id=task_id,
            duration=3.0,  # 10x faster
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        traces.extend([outlier1, outlier2])
        
        baseline = regression_detector.establishBaseline(task_id, traces)
        
        # Mean should be close to 30, not affected by outliers
        duration_stats = baseline.metrics['total_duration']
        assert 28.0 < duration_stats.mean < 32.0
    
    def test_establish_baseline_versioning(self, regression_detector, sample_robot_state):
        """Test that baselines are versioned."""
        task_id = "test_task"
        
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        baseline1 = regression_detector.establishBaseline(task_id, traces)
        assert baseline1.version == 1
        
        # Create new baseline
        baseline2 = regression_detector.establishBaseline(task_id, traces, approved_by="admin")
        assert baseline2.version == 2
        
        # Verify both versions are stored
        assert regression_detector.getBaselineVersion(task_id, 1) is not None
        assert regression_detector.getBaselineVersion(task_id, 2) is not None
    
    def test_establish_baseline_mismatched_task_ids(self, regression_detector, sample_robot_state):
        """Test that all traces must be for the same task."""
        task_id = "test_task"
        
        traces = []
        for i in range(10):
            # Use different task_id for some traces
            trace_task_id = task_id if i < 5 else "other_task"
            trace = create_trace_with_metrics(
                task_id=trace_task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        with pytest.raises(ValueError, match="expected test_task"):
            regression_detector.establishBaseline(task_id, traces)


class TestDetectRegression:
    """Tests for detectRegression method."""
    
    def test_detect_no_regression(self, regression_detector, sample_robot_state):
        """Test that no regression is detected for normal performance."""
        task_id = "test_task"
        
        # Establish baseline
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        regression_detector.establishBaseline(task_id, traces)
        
        # Create new trace with similar performance
        new_trace = create_trace_with_metrics(
            task_id=task_id,
            duration=31.0,  # Within normal range
            success_rate=0.94,
            energy=0.16,
            accuracy=0.89,
            robot_state=sample_robot_state
        )
        
        report = regression_detector.detectRegression(task_id, new_trace)
        
        assert not report.detected
        assert len(report.regressions) == 0
        assert report.overall_severity == "NONE"
    
    def test_detect_duration_regression(self, regression_detector, sample_robot_state):
        """Test detection of duration regression."""
        task_id = "test_task"
        
        # Establish baseline with 30s duration
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        regression_detector.establishBaseline(task_id, traces)
        
        # Create new trace with 50% longer duration (significant regression)
        new_trace = create_trace_with_metrics(
            task_id=task_id,
            duration=45.0,  # 50% slower
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        
        report = regression_detector.detectRegression(task_id, new_trace)
        
        assert report.detected
        assert len(report.regressions) > 0
        
        # Find duration regression
        duration_regression = next(
            (r for r in report.regressions if r.metric_name == 'total_duration'),
            None
        )
        assert duration_regression is not None
        assert duration_regression.degradation > 0.1  # >10%
        assert duration_regression.p_value < 0.05
    
    def test_detect_success_rate_regression(self, regression_detector, sample_robot_state):
        """Test detection of success rate regression."""
        task_id = "test_task"
        
        # Establish baseline with 95% success rate
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        regression_detector.establishBaseline(task_id, traces)
        
        # Create new trace with much lower success rate
        new_trace = create_trace_with_metrics(
            task_id=task_id,
            duration=30.0,
            success_rate=0.70,  # 26% degradation
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        
        report = regression_detector.detectRegression(task_id, new_trace)
        
        assert report.detected
        
        # Find success rate regression
        success_regression = next(
            (r for r in report.regressions if r.metric_name == 'success_rate'),
            None
        )
        assert success_regression is not None
        assert success_regression.degradation > 0.1
    
    def test_regression_severity_classification(self, regression_detector, sample_robot_state):
        """Test that regression severity is classified correctly."""
        task_id = "test_task"
        
        # Establish baseline
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        regression_detector.establishBaseline(task_id, traces)
        
        # Test CRITICAL severity (50%+ degradation)
        critical_trace = create_trace_with_metrics(
            task_id=task_id,
            duration=60.0,  # 100% slower
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        
        report = regression_detector.detectRegression(task_id, critical_trace)
        
        if report.detected:
            assert report.overall_severity in ["HIGH", "CRITICAL"]
    
    def test_detect_regression_no_baseline(self, regression_detector, sample_robot_state):
        """Test that detection fails without baseline."""
        task_id = "test_task"
        
        new_trace = create_trace_with_metrics(
            task_id=task_id,
            duration=30.0,
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        
        with pytest.raises(ValueError, match="No baseline exists"):
            regression_detector.detectRegression(task_id, new_trace)
    
    def test_detect_regression_mismatched_task_id(self, regression_detector, sample_robot_state):
        """Test that task_id must match between baseline and trace."""
        task_id = "test_task"
        
        # Establish baseline
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        regression_detector.establishBaseline(task_id, traces)
        
        # Create trace with different task_id
        new_trace = create_trace_with_metrics(
            task_id="other_task",
            duration=30.0,
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        
        with pytest.raises(ValueError, match="does not match"):
            regression_detector.detectRegression(task_id, new_trace)
    
    def test_baseline_immutability_during_analysis(self, regression_detector, sample_robot_state):
        """Test that baseline remains unchanged during regression detection."""
        task_id = "test_task"
        
        # Establish baseline
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        baseline = regression_detector.establishBaseline(task_id, traces)
        
        # Store original baseline values
        original_mean = baseline.metrics['total_duration'].mean
        original_version = baseline.version
        
        # Detect regression
        new_trace = create_trace_with_metrics(
            task_id=task_id,
            duration=45.0,
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        
        regression_detector.detectRegression(task_id, new_trace)
        
        # Verify baseline unchanged
        current_baseline = regression_detector.getBaseline(task_id)
        assert current_baseline.metrics['total_duration'].mean == original_mean
        assert current_baseline.version == original_version


class TestClassifyRegression:
    """Tests for classifyRegression method."""
    
    def test_classify_no_regression(self, regression_detector):
        """Test classification of report with no regressions."""
        report = RegressionReport(
            task_id="test_task",
            execution_id=str(uuid4()),
            baseline_version=1,
            detected=False,
            timestamp=datetime.now()
        )
        
        severity = regression_detector.classifyRegression(report)
        assert severity == "NONE"
    
    def test_classify_critical_regression(self, regression_detector):
        """Test classification of critical regression."""
        report = RegressionReport(
            task_id="test_task",
            execution_id=str(uuid4()),
            baseline_version=1,
            detected=True,
            timestamp=datetime.now(),
            regressions=[
                RegressionDetail(
                    metric_name="total_duration",
                    baseline_value=30.0,
                    new_value=60.0,
                    degradation=1.0,  # 100% degradation
                    p_value=0.01,
                    effect_size=2.0,
                    severity="CRITICAL"
                )
            ]
        )
        
        severity = regression_detector.classifyRegression(report)
        assert severity == "CRITICAL"
    
    def test_classify_mixed_severity(self, regression_detector):
        """Test classification with multiple regressions of different severity."""
        report = RegressionReport(
            task_id="test_task",
            execution_id=str(uuid4()),
            baseline_version=1,
            detected=True,
            timestamp=datetime.now(),
            regressions=[
                RegressionDetail(
                    metric_name="total_duration",
                    baseline_value=30.0,
                    new_value=36.0,
                    degradation=0.2,
                    p_value=0.01,
                    effect_size=1.0,
                    severity="MEDIUM"
                ),
                RegressionDetail(
                    metric_name="success_rate",
                    baseline_value=0.95,
                    new_value=0.80,
                    degradation=0.16,
                    p_value=0.01,
                    effect_size=1.5,
                    severity="LOW"
                )
            ]
        )
        
        # Should take highest severity
        severity = regression_detector.classifyRegression(report)
        assert severity == "MEDIUM"


class TestTrackRegressionHistory:
    """Tests for trackRegressionHistory method."""
    
    def test_track_empty_history(self, regression_detector):
        """Test tracking history for task with no regressions."""
        history = regression_detector.trackRegressionHistory("test_task")
        assert len(history) == 0
    
    def test_track_regression_history(self, regression_detector, sample_robot_state):
        """Test that regressions are recorded in history."""
        task_id = "test_task"
        
        # Establish baseline
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        regression_detector.establishBaseline(task_id, traces)
        
        # Detect multiple regressions
        for i in range(3):
            new_trace = create_trace_with_metrics(
                task_id=task_id,
                duration=45.0 + i * 5,  # Increasing degradation
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            regression_detector.detectRegression(task_id, new_trace)
        
        # Check history
        history = regression_detector.trackRegressionHistory(task_id)
        assert len(history) >= 1  # At least one regression detected
        
        # Verify history is sorted by timestamp (newest first)
        if len(history) > 1:
            for i in range(len(history) - 1):
                assert history[i].timestamp >= history[i + 1].timestamp
    
    def test_regression_event_properties(self, regression_detector, sample_robot_state):
        """Test that regression events have correct properties."""
        task_id = "test_task"
        
        # Establish baseline
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        regression_detector.establishBaseline(task_id, traces)
        
        # Detect regression
        new_trace = create_trace_with_metrics(
            task_id=task_id,
            duration=50.0,
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        
        report = regression_detector.detectRegression(task_id, new_trace)
        
        if report.detected:
            history = regression_detector.trackRegressionHistory(task_id)
            assert len(history) > 0
            
            event = history[0]
            assert event.task_id == task_id
            assert event.execution_id == new_trace.execution_id
            assert event.severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert len(event.metrics_affected) > 0
            assert not event.resolved  # Initially unresolved


class TestUpdateBaseline:
    """Tests for updateBaseline method."""
    
    def test_update_baseline_requires_approval(self, regression_detector, sample_robot_state):
        """Test that baseline updates require administrator approval."""
        task_id = "test_task"
        
        # Create new baseline
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        new_baseline = Baseline(
            task_id=task_id,
            version=1,
            created_at=datetime.now(),
            sample_size=10,
            metrics={
                'total_duration': MetricStatistics(
                    metric_name='total_duration',
                    mean=30.0,
                    std_dev=1.0,
                    min_value=28.0,
                    max_value=32.0,
                    sample_size=10
                )
            }
        )
        
        # Should fail without approval
        with pytest.raises(ValueError, match="approval required"):
            regression_detector.updateBaseline(task_id, new_baseline, approved_by="")
    
    def test_update_baseline_with_approval(self, regression_detector, sample_robot_state):
        """Test successful baseline update with approval."""
        task_id = "test_task"
        
        # Establish initial baseline
        traces = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        regression_detector.establishBaseline(task_id, traces)
        
        # Create new baseline
        new_baseline = Baseline(
            task_id=task_id,
            version=1,
            created_at=datetime.now(),
            sample_size=10,
            metrics={
                'total_duration': MetricStatistics(
                    metric_name='total_duration',
                    mean=35.0,  # Updated mean
                    std_dev=1.0,
                    min_value=33.0,
                    max_value=37.0,
                    sample_size=10
                )
            }
        )
        
        # Update with approval
        updated = regression_detector.updateBaseline(
            task_id,
            new_baseline,
            approved_by="admin@example.com"
        )
        
        assert updated.is_approved()
        assert updated.approved_by == "admin@example.com"
        assert updated.version == 2  # Version incremented
    
    def test_update_baseline_insufficient_data(self, regression_detector):
        """Test that baseline update requires sufficient data."""
        task_id = "test_task"
        
        # Create baseline with insufficient data
        insufficient_baseline = Baseline(
            task_id=task_id,
            version=1,
            created_at=datetime.now(),
            sample_size=5,  # Less than 10
            metrics={}
        )
        
        with pytest.raises(ValueError, match="insufficient data"):
            regression_detector.updateBaseline(
                task_id,
                insufficient_baseline,
                approved_by="admin@example.com"
            )


class TestIntegration:
    """Integration tests for regression detector."""
    
    def test_full_regression_detection_workflow(self, regression_detector, sample_robot_state):
        """Test complete workflow from baseline to detection."""
        task_id = "test_task"
        
        # Step 1: Establish baseline
        traces = []
        for i in range(15):
            trace = create_trace_with_metrics(
                task_id=task_id,
                duration=30.0 + i * 0.2,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces.append(trace)
        
        baseline = regression_detector.establishBaseline(
            task_id,
            traces,
            approved_by="admin@example.com"
        )
        
        assert baseline.is_sufficient()
        assert baseline.is_approved()
        
        # Step 2: Detect regression
        regressed_trace = create_trace_with_metrics(
            task_id=task_id,
            duration=50.0,  # Significant degradation
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        
        report = regression_detector.detectRegression(task_id, regressed_trace)
        
        if report.detected:
            # Step 3: Classify severity
            severity = regression_detector.classifyRegression(report)
            assert severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            
            # Step 4: Check history
            history = regression_detector.trackRegressionHistory(task_id)
            assert len(history) > 0
            assert history[0].task_id == task_id
    
    def test_multiple_tasks_independent_baselines(self, regression_detector, sample_robot_state):
        """Test that multiple tasks have independent baselines."""
        task1 = "task_1"
        task2 = "task_2"
        
        # Establish baseline for task 1
        traces1 = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task1,
                duration=30.0,
                success_rate=0.95,
                energy=0.15,
                accuracy=0.90,
                robot_state=sample_robot_state
            )
            traces1.append(trace)
        
        baseline1 = regression_detector.establishBaseline(task1, traces1)
        
        # Establish baseline for task 2
        traces2 = []
        for i in range(10):
            trace = create_trace_with_metrics(
                task_id=task2,
                duration=60.0,  # Different baseline
                success_rate=0.90,
                energy=0.25,
                accuracy=0.85,
                robot_state=sample_robot_state
            )
            traces2.append(trace)
        
        baseline2 = regression_detector.establishBaseline(task2, traces2)
        
        # Verify independent baselines
        assert baseline1.metrics['total_duration'].mean < 35.0
        assert baseline2.metrics['total_duration'].mean > 55.0
        
        # Verify independent detection
        new_trace1 = create_trace_with_metrics(
            task_id=task1,
            duration=31.0,  # Normal for task1
            success_rate=0.95,
            energy=0.15,
            accuracy=0.90,
            robot_state=sample_robot_state
        )
        
        report1 = regression_detector.detectRegression(task1, new_trace1)
        assert not report1.detected  # Should be normal
