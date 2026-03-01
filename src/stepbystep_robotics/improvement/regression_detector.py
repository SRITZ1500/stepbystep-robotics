"""
Regression Detector for identifying performance degradations and behavioral anomalies.

This module implements the RegressionDetector component which establishes performance
baselines, detects statistically significant regressions, classifies severity, and
tracks regression trends over time.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID
import math
import statistics

from ..models import ExecutionTrace, PerformanceMetrics


@dataclass
class MetricStatistics:
    """Statistical summary of a performance metric."""
    metric_name: str
    mean: float
    std_dev: float
    min_value: float
    max_value: float
    sample_size: int
    
    def is_valid(self) -> bool:
        """Check if statistics are valid."""
        return (
            self.sample_size > 0 and
            self.std_dev >= 0 and
            self.min_value <= self.mean <= self.max_value and
            not math.isnan(self.mean) and
            not math.isnan(self.std_dev)
        )


@dataclass
class Baseline:
    """Performance baseline for a task."""
    task_id: str
    version: int
    created_at: datetime
    sample_size: int
    metrics: Dict[str, MetricStatistics]
    execution_ids: List[str] = field(default_factory=list)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    def is_sufficient(self) -> bool:
        """Check if baseline has sufficient data (minimum 10 executions)."""
        return self.sample_size >= 10
    
    def is_approved(self) -> bool:
        """Check if baseline has been approved by administrator."""
        return self.approved_by is not None and self.approved_at is not None


@dataclass
class RegressionDetail:
    """Details of a detected regression for a specific metric."""
    metric_name: str
    baseline_value: float
    new_value: float
    degradation: float  # Percentage degradation
    p_value: float
    effect_size: float
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"


@dataclass
class RegressionReport:
    """Report of regression detection analysis."""
    task_id: str
    execution_id: str
    baseline_version: int
    detected: bool
    timestamp: datetime
    regressions: List[RegressionDetail] = field(default_factory=list)
    overall_severity: str = "NONE"  # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    recommendation: str = ""
    statistical_summary: Dict[str, float] = field(default_factory=dict)


@dataclass
class RegressionEvent:
    """Historical record of a regression detection."""
    timestamp: datetime
    task_id: str
    execution_id: str
    severity: str
    metrics_affected: List[str]
    resolved: bool = False
    resolution_notes: Optional[str] = None


class RegressionDetector:
    """
    Identifies performance regressions and behavioral anomalies.
    
    The RegressionDetector establishes performance baselines from historical data,
    detects statistically significant degradations using t-tests, classifies
    regression severity, and tracks trends over time.
    
    Requirements:
        - 8.1: Establish baselines from minimum 10 executions
        - 8.2: Detect regressions using statistical tests
        - 8.3: Detect degradation >10% with p<0.05, effect size >0.5
        - 8.4: Classify regression severity
        - 8.5: Track regression history
    """
    
    def __init__(self):
        """Initialize the regression detector."""
        self._baselines: Dict[str, Baseline] = {}
        self._regression_history: Dict[str, List[RegressionEvent]] = {}
        self._baseline_versions: Dict[str, List[Baseline]] = {}
    
    def establishBaseline(
        self,
        task_id: str,
        traces: List[ExecutionTrace],
        approved_by: Optional[str] = None
    ) -> Baseline:
        """
        Establish a performance baseline from historical execution traces.
        
        This method computes statistical summaries (mean, std dev, min, max) for
        all performance metrics across the provided traces. Requires minimum 10
        executions for statistical validity.
        
        Args:
            task_id: Task identifier
            traces: List of historical execution traces (minimum 10)
            approved_by: Optional administrator who approved this baseline
        
        Returns:
            Baseline with computed statistics
        
        Raises:
            ValueError: If fewer than 10 traces provided
        
        Requirements:
            - 8.1: Require minimum 10 executions for baseline
            - 14.1: Require administrator approval for baseline updates
            - 14.3: Perform statistical outlier detection
            - 14.4: Maintain versioned baselines
        """
        if len(traces) < 10:
            raise ValueError(
                f"Insufficient traces for baseline: {len(traces)} provided, minimum 10 required"
            )
        
        # Verify all traces are for the same task
        for trace in traces:
            if trace.task_id != task_id:
                raise ValueError(
                    f"Trace {trace.execution_id} is for task {trace.task_id}, expected {task_id}"
                )
        
        # Collect metric values from all traces
        metric_values: Dict[str, List[float]] = {}
        execution_ids = []
        
        for trace in traces:
            if trace.performance_metrics is None:
                continue
            
            execution_ids.append(trace.execution_id)
            metrics = trace.performance_metrics
            
            # Collect all numeric metrics
            for metric_name in ['total_duration', 'success_rate', 'energy_consumed',
                               'accuracy_score', 'smoothness_score', 'safety_score']:
                value = getattr(metrics, metric_name, None)
                if value is not None:
                    if metric_name not in metric_values:
                        metric_values[metric_name] = []
                    metric_values[metric_name].append(value)
        
        # Compute statistics for each metric
        metric_stats = {}
        for metric_name, values in metric_values.items():
            if len(values) < 10:
                continue
            
            # Remove outliers using IQR method (Requirement 14.3)
            cleaned_values = self._remove_outliers(values)
            
            if len(cleaned_values) >= 10:
                metric_stats[metric_name] = MetricStatistics(
                    metric_name=metric_name,
                    mean=statistics.mean(cleaned_values),
                    std_dev=statistics.stdev(cleaned_values) if len(cleaned_values) > 1 else 0.0,
                    min_value=min(cleaned_values),
                    max_value=max(cleaned_values),
                    sample_size=len(cleaned_values)
                )
        
        # Determine version (Requirement 14.4)
        if task_id in self._baseline_versions:
            version = len(self._baseline_versions[task_id]) + 1
        else:
            version = 1
            self._baseline_versions[task_id] = []
        
        # Create baseline
        baseline = Baseline(
            task_id=task_id,
            version=version,
            created_at=datetime.now(),
            sample_size=len(execution_ids),
            metrics=metric_stats,
            execution_ids=execution_ids,
            approved_by=approved_by,
            approved_at=datetime.now() if approved_by else None
        )
        
        # Store baseline
        self._baselines[task_id] = baseline
        self._baseline_versions[task_id].append(baseline)
        
        return baseline
    
    def detectRegression(
        self,
        task_id: str,
        new_trace: ExecutionTrace
    ) -> RegressionReport:
        """
        Detect performance regressions by comparing new execution to baseline.
        
        This method performs statistical hypothesis testing (two-sample t-test) to
        identify significant performance degradations. Detects regressions when
        degradation >10% with p<0.05 and effect size >0.5.
        
        Args:
            task_id: Task identifier
            new_trace: New execution trace to analyze
        
        Returns:
            RegressionReport with detection results
        
        Raises:
            ValueError: If no baseline exists for task or trace is incomplete
        
        Requirements:
            - 8.2: Detect statistically significant performance degradations
            - 8.3: Detect degradation >10% with p<0.05, effect size >0.5
            - 8.6: Baseline remains unchanged during analysis
        """
        # Validate inputs
        if task_id not in self._baselines:
            raise ValueError(f"No baseline exists for task {task_id}")
        
        if new_trace.task_id != task_id:
            raise ValueError(
                f"Trace task_id {new_trace.task_id} does not match requested task_id {task_id}"
            )
        
        if new_trace.performance_metrics is None:
            raise ValueError(f"Trace {new_trace.execution_id} has no performance metrics")
        
        baseline = self._baselines[task_id]
        
        if not baseline.is_sufficient():
            raise ValueError(
                f"Baseline for task {task_id} has insufficient data: "
                f"{baseline.sample_size} samples, minimum 10 required"
            )
        
        # Create report
        report = RegressionReport(
            task_id=task_id,
            execution_id=new_trace.execution_id,
            baseline_version=baseline.version,
            detected=False,
            timestamp=datetime.now()
        )
        
        # Compare each metric against baseline (Requirement 8.6: baseline unchanged)
        new_metrics = new_trace.performance_metrics
        regressions = []
        
        for metric_name, baseline_stats in baseline.metrics.items():
            # Get new value
            new_value = getattr(new_metrics, metric_name, None)
            if new_value is None:
                continue
            
            # Perform statistical test (two-sample t-test)
            test_result = self._perform_t_test(
                new_value,
                baseline_stats.mean,
                baseline_stats.std_dev,
                baseline_stats.sample_size
            )
            
            # Check for significant degradation (Requirement 8.3)
            if test_result['p_value'] < 0.05 and test_result['effect_size'] > 0.5:
                degradation = self._calculate_degradation(new_value, baseline_stats.mean, metric_name)
                
                if degradation > 0.1:  # 10% threshold
                    severity = self._classify_degradation_severity(degradation)
                    
                    regression = RegressionDetail(
                        metric_name=metric_name,
                        baseline_value=baseline_stats.mean,
                        new_value=new_value,
                        degradation=degradation,
                        p_value=test_result['p_value'],
                        effect_size=test_result['effect_size'],
                        severity=severity
                    )
                    regressions.append(regression)
        
        # Update report
        if regressions:
            report.detected = True
            report.regressions = regressions
            report.overall_severity = self._determine_overall_severity(regressions)
            report.recommendation = self._generate_recommendation(regressions)
            
            # Record in history
            self._record_regression_event(task_id, new_trace.execution_id, report)
        
        # Add statistical summary
        report.statistical_summary = {
            'baseline_version': baseline.version,
            'baseline_sample_size': baseline.sample_size,
            'metrics_compared': len(baseline.metrics),
            'regressions_detected': len(regressions)
        }
        
        return report
    
    def classifyRegression(self, report: RegressionReport) -> str:
        """
        Classify the overall severity of a regression report.
        
        Args:
            report: Regression report to classify
        
        Returns:
            Severity classification: "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
        
        Requirements:
            - 8.4: Classify regression severity based on impact
        """
        if not report.detected or not report.regressions:
            return "NONE"
        
        return self._determine_overall_severity(report.regressions)
    
    def trackRegressionHistory(self, task_id: str) -> List[RegressionEvent]:
        """
        Get the regression history for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            List of regression events, sorted by timestamp (newest first)
        
        Requirements:
            - 8.5: Track regression trends over time
        """
        if task_id not in self._regression_history:
            return []
        
        # Return copy sorted by timestamp (newest first)
        history = self._regression_history[task_id].copy()
        history.sort(key=lambda e: e.timestamp, reverse=True)
        return history
    
    def getBaseline(self, task_id: str) -> Optional[Baseline]:
        """Get the current baseline for a task."""
        return self._baselines.get(task_id)
    
    def getBaselineVersion(self, task_id: str, version: int) -> Optional[Baseline]:
        """Get a specific version of a baseline."""
        if task_id not in self._baseline_versions:
            return None
        
        for baseline in self._baseline_versions[task_id]:
            if baseline.version == version:
                return baseline
        
        return None
    
    def updateBaseline(
        self,
        task_id: str,
        new_baseline: Baseline,
        approved_by: str
    ) -> Baseline:
        """
        Update baseline with administrator approval.
        
        Args:
            task_id: Task identifier
            new_baseline: New baseline to apply
            approved_by: Administrator approving the update
        
        Returns:
            Updated baseline
        
        Requirements:
            - 14.1: Require administrator approval for baseline updates
            - 14.2: Validate baseline before applying
        """
        if not approved_by:
            raise ValueError("Administrator approval required for baseline updates")
        
        if not new_baseline.is_sufficient():
            raise ValueError(
                f"New baseline has insufficient data: "
                f"{new_baseline.sample_size} samples, minimum 10 required"
            )
        
        # Validate all metric statistics
        for metric_name, stats in new_baseline.metrics.items():
            if not stats.is_valid():
                raise ValueError(f"Invalid statistics for metric {metric_name}")
        
        # Mark as approved
        new_baseline.approved_by = approved_by
        new_baseline.approved_at = datetime.now()
        
        # Update version if needed
        if task_id in self._baseline_versions:
            new_baseline.version = len(self._baseline_versions[task_id]) + 1
        else:
            new_baseline.version = 1
            self._baseline_versions[task_id] = []
        
        # Store
        self._baselines[task_id] = new_baseline
        self._baseline_versions[task_id].append(new_baseline)
        
        return new_baseline
    
    # Private helper methods
    
    def _remove_outliers(self, values: List[float]) -> List[float]:
        """Remove outliers using IQR method."""
        if len(values) < 4:
            return values
        
        sorted_values = sorted(values)
        q1_idx = len(sorted_values) // 4
        q3_idx = 3 * len(sorted_values) // 4
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        return [v for v in values if lower_bound <= v <= upper_bound]
    
    def _perform_t_test(
        self,
        new_value: float,
        baseline_mean: float,
        baseline_std: float,
        baseline_n: int
    ) -> Dict[str, float]:
        """Perform two-sample t-test."""
        # Simplified t-test for single new value vs baseline
        if baseline_std == 0:
            baseline_std = 0.01  # Avoid division by zero
        
        # Calculate t-statistic
        t_stat = abs(new_value - baseline_mean) / (baseline_std / math.sqrt(baseline_n))
        
        # Approximate p-value (simplified)
        # For large n, t-distribution approaches normal distribution
        # This is a rough approximation
        if t_stat > 2.576:  # 99% confidence
            p_value = 0.01
        elif t_stat > 1.96:  # 95% confidence
            p_value = 0.05
        elif t_stat > 1.645:  # 90% confidence
            p_value = 0.10
        else:
            p_value = 0.20
        
        # Calculate effect size (Cohen's d)
        effect_size = abs(new_value - baseline_mean) / baseline_std if baseline_std > 0 else 0.0
        
        return {
            'p_value': p_value,
            'effect_size': effect_size,
            't_statistic': t_stat
        }
    
    def _calculate_degradation(
        self,
        new_value: float,
        baseline_value: float,
        metric_name: str
    ) -> float:
        """Calculate percentage degradation (positive = worse performance)."""
        if baseline_value == 0:
            return 0.0
        
        # For metrics where higher is better (success_rate, accuracy, smoothness, safety)
        if metric_name in ['success_rate', 'accuracy_score', 'smoothness_score', 'safety_score']:
            # Degradation = (baseline - new) / baseline
            return (baseline_value - new_value) / baseline_value
        else:
            # For metrics where lower is better (duration, energy)
            # Degradation = (new - baseline) / baseline
            return (new_value - baseline_value) / baseline_value
    
    def _classify_degradation_severity(self, degradation: float) -> str:
        """Classify degradation severity based on magnitude."""
        if degradation >= 0.5:  # 50% or more
            return "CRITICAL"
        elif degradation >= 0.3:  # 30-50%
            return "HIGH"
        elif degradation >= 0.2:  # 20-30%
            return "MEDIUM"
        else:  # 10-20%
            return "LOW"
    
    def _determine_overall_severity(self, regressions: List[RegressionDetail]) -> str:
        """Determine overall severity from multiple regressions."""
        if not regressions:
            return "NONE"
        
        # Take the highest severity
        severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
        max_severity = max(regressions, key=lambda r: severity_order.get(r.severity, 0))
        return max_severity.severity
    
    def _generate_recommendation(self, regressions: List[RegressionDetail]) -> str:
        """Generate recommendation based on detected regressions."""
        if not regressions:
            return "No action needed - performance within baseline"
        
        critical_count = sum(1 for r in regressions if r.severity == "CRITICAL")
        high_count = sum(1 for r in regressions if r.severity == "HIGH")
        
        if critical_count > 0:
            return (
                f"URGENT: {critical_count} critical regression(s) detected. "
                "Immediate investigation required. Consider rolling back recent changes."
            )
        elif high_count > 0:
            return (
                f"WARNING: {high_count} high-severity regression(s) detected. "
                "Review recent changes and investigate root cause."
            )
        else:
            return (
                f"{len(regressions)} regression(s) detected. "
                "Monitor performance and consider optimization if trend continues."
            )
    
    def _record_regression_event(
        self,
        task_id: str,
        execution_id: str,
        report: RegressionReport
    ) -> None:
        """Record a regression event in history."""
        if task_id not in self._regression_history:
            self._regression_history[task_id] = []
        
        event = RegressionEvent(
            timestamp=report.timestamp,
            task_id=task_id,
            execution_id=execution_id,
            severity=report.overall_severity,
            metrics_affected=[r.metric_name for r in report.regressions]
        )
        
        self._regression_history[task_id].append(event)
