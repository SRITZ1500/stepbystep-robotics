"""
Improvement Pipeline for wiring Improvement Layer components together.

This module connects ExecutionTracker → EvaluationEngine → RegressionDetector
to create a complete feedback loop for continuous performance improvement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from ..models import ExecutionTrace, PerformanceMetrics
from ..workflow.execution_tracker import ExecutionTracker
from .evaluation_engine import EvaluationEngine, Recommendation, BottleneckInfo
from .regression_detector import RegressionDetector, RegressionReport, Baseline


@dataclass
class ImprovementAnalysis:
    """Complete improvement analysis for an execution."""
    execution_id: str
    task_id: str
    timestamp: datetime
    
    # Evaluation results
    metrics: PerformanceMetrics
    bottlenecks: List[BottleneckInfo]
    recommendations: List[Recommendation]
    
    # Regression detection results
    regression_report: Optional[RegressionReport] = None
    baseline_version: Optional[int] = None
    
    # Summary
    overall_health: str = "GOOD"  # "EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL"
    action_required: bool = False
    priority_actions: List[str] = field(default_factory=list)


class ImprovementPipeline:
    """
    Wires Improvement Layer components into a complete feedback loop.
    
    The ImprovementPipeline connects:
    - ExecutionTracker → EvaluationEngine (traces to metrics)
    - EvaluationEngine → RegressionDetector (metrics to regression detection)
    - Creates end-to-end improvement workflow
    
    Requirements:
        - 7.1: Compute performance metrics from execution traces
        - 8.2: Detect regressions using statistical tests
        - Integration of all Improvement Layer components
    """
    
    def __init__(
        self,
        execution_tracker: ExecutionTracker,
        evaluation_engine: EvaluationEngine,
        regression_detector: RegressionDetector
    ):
        """
        Initialize the improvement pipeline.
        
        Args:
            execution_tracker: Tracker for execution traces
            evaluation_engine: Engine for performance evaluation
            regression_detector: Detector for performance regressions
        """
        self.execution_tracker = execution_tracker
        self.evaluation_engine = evaluation_engine
        self.regression_detector = regression_detector
    
    def analyzeExecution(
        self,
        execution_id: str,
        check_regression: bool = True
    ) -> ImprovementAnalysis:
        """
        Perform complete improvement analysis on an execution.
        
        This method orchestrates the full improvement pipeline:
        1. Retrieve execution trace from tracker
        2. Evaluate performance metrics
        3. Identify bottlenecks
        4. Generate recommendations
        5. Check for regressions (if baseline exists)
        6. Determine overall health and required actions
        
        Args:
            execution_id: Execution to analyze
            check_regression: Whether to check for regressions
        
        Returns:
            Complete improvement analysis
        
        Raises:
            ValueError: If execution not found
        """
        # Step 1: Get execution trace
        trace = self.execution_tracker.getExecutionTrace(execution_id)
        
        # Step 2: Evaluate performance
        metrics = self.evaluation_engine.evaluateExecution(trace)
        
        # Step 3: Identify bottlenecks
        bottlenecks = self.evaluation_engine.identifyBottlenecks(trace)
        
        # Step 4: Generate recommendations
        recommendations = self.evaluation_engine.generateRecommendations(metrics, trace)
        
        # Step 5: Check for regressions (if baseline exists)
        regression_report = None
        baseline_version = None
        
        if check_regression:
            baseline = self.regression_detector.getBaseline(trace.task_id)
            if baseline is not None:
                baseline_version = baseline.version
                try:
                    regression_report = self.regression_detector.detectRegression(
                        trace.task_id,
                        trace
                    )
                except ValueError:
                    # No baseline or insufficient data - skip regression check
                    pass
        
        # Step 6: Determine overall health
        overall_health = self._determine_overall_health(
            metrics,
            bottlenecks,
            recommendations,
            regression_report
        )
        
        # Step 7: Identify priority actions
        action_required, priority_actions = self._identify_priority_actions(
            bottlenecks,
            recommendations,
            regression_report
        )
        
        return ImprovementAnalysis(
            execution_id=execution_id,
            task_id=trace.task_id,
            timestamp=datetime.now(),
            metrics=metrics,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            regression_report=regression_report,
            baseline_version=baseline_version,
            overall_health=overall_health,
            action_required=action_required,
            priority_actions=priority_actions
        )
    
    def establishBaselineFromHistory(
        self,
        task_id: str,
        min_executions: int = 10,
        approved_by: Optional[str] = None
    ) -> Baseline:
        """
        Establish baseline from execution history.
        
        This method retrieves recent successful executions from the tracker
        and uses them to establish a performance baseline.
        
        Args:
            task_id: Task to establish baseline for
            min_executions: Minimum number of executions required
            approved_by: Optional administrator approval
        
        Returns:
            Established baseline
        
        Raises:
            ValueError: If insufficient execution history
        """
        # Get all executions for this task
        # Note: In production, this would query a database with filters
        # For now, we'll need the caller to provide traces
        raise NotImplementedError(
            "establishBaselineFromHistory requires database integration. "
            "Use regression_detector.establishBaseline() directly with traces."
        )
    
    def compareExecutions(
        self,
        execution_id_a: str,
        execution_id_b: str
    ) -> Dict:
        """
        Compare two executions to identify performance differences.
        
        Args:
            execution_id_a: First execution
            execution_id_b: Second execution
        
        Returns:
            Comparison report with detailed analysis
        """
        # Get traces
        trace_a = self.execution_tracker.getExecutionTrace(execution_id_a)
        trace_b = self.execution_tracker.getExecutionTrace(execution_id_b)
        
        # Compare using evaluation engine
        comparison = self.evaluation_engine.compareExecutions(trace_a, trace_b)
        
        # Analyze both executions
        analysis_a = self.analyzeExecution(execution_id_a, check_regression=False)
        analysis_b = self.analyzeExecution(execution_id_b, check_regression=False)
        
        return {
            'comparison': comparison,
            'execution_a': {
                'id': execution_id_a,
                'health': analysis_a.overall_health,
                'bottlenecks': len(analysis_a.bottlenecks),
                'recommendations': len(analysis_a.recommendations)
            },
            'execution_b': {
                'id': execution_id_b,
                'health': analysis_b.overall_health,
                'bottlenecks': len(analysis_b.bottlenecks),
                'recommendations': len(analysis_b.recommendations)
            },
            'winner': self._determine_winner(analysis_a, analysis_b)
        }
    
    def trackTaskHealth(self, task_id: str) -> Dict:
        """
        Track overall health of a task based on regression history.
        
        Args:
            task_id: Task to track
        
        Returns:
            Health summary with trends
        """
        # Get regression history
        history = self.regression_detector.trackRegressionHistory(task_id)
        
        # Get baseline
        baseline = self.regression_detector.getBaseline(task_id)
        
        # Analyze trends
        recent_regressions = [
            event for event in history[:10]  # Last 10 events
            if not event.resolved
        ]
        
        critical_count = sum(1 for e in recent_regressions if e.severity == "CRITICAL")
        high_count = sum(1 for e in recent_regressions if e.severity == "HIGH")
        
        # Determine health
        if critical_count > 0:
            health = "CRITICAL"
            trend = "DEGRADING"
        elif high_count > 2:
            health = "POOR"
            trend = "DEGRADING"
        elif len(recent_regressions) > 5:
            health = "FAIR"
            trend = "UNSTABLE"
        elif len(recent_regressions) > 0:
            health = "GOOD"
            trend = "STABLE"
        else:
            health = "EXCELLENT"
            trend = "STABLE"
        
        return {
            'task_id': task_id,
            'health': health,
            'trend': trend,
            'baseline_version': baseline.version if baseline else None,
            'baseline_approved': baseline.is_approved() if baseline else False,
            'total_regressions': len(history),
            'unresolved_regressions': len(recent_regressions),
            'critical_regressions': critical_count,
            'high_regressions': high_count,
            'recommendation': self._generate_health_recommendation(
                health,
                critical_count,
                high_count,
                len(recent_regressions)
            )
        }
    
    def generateImprovementReport(
        self,
        task_id: str,
        recent_executions: int = 10
    ) -> Dict:
        """
        Generate comprehensive improvement report for a task.
        
        Args:
            task_id: Task to report on
            recent_executions: Number of recent executions to analyze
        
        Returns:
            Comprehensive improvement report
        """
        # Get task health
        health = self.trackTaskHealth(task_id)
        
        # Get baseline
        baseline = self.regression_detector.getBaseline(task_id)
        
        # Get regression history
        history = self.regression_detector.trackRegressionHistory(task_id)
        
        return {
            'task_id': task_id,
            'generated_at': datetime.now().isoformat(),
            'health': health,
            'baseline': {
                'version': baseline.version if baseline else None,
                'sample_size': baseline.sample_size if baseline else 0,
                'approved': baseline.is_approved() if baseline else False,
                'created_at': baseline.created_at.isoformat() if baseline else None
            },
            'regression_summary': {
                'total_events': len(history),
                'recent_events': len(history[:10]),
                'severity_distribution': self._count_severity_distribution(history)
            },
            'recommendations': health['recommendation']
        }
    
    # Private helper methods
    
    def _determine_overall_health(
        self,
        metrics: PerformanceMetrics,
        bottlenecks: List[BottleneckInfo],
        recommendations: List[Recommendation],
        regression_report: Optional[RegressionReport]
    ) -> str:
        """Determine overall health status."""
        # Check for critical issues
        critical_bottlenecks = [b for b in bottlenecks if b.severity == "CRITICAL"]
        critical_recommendations = [r for r in recommendations if r.priority == "CRITICAL"]
        
        if regression_report and regression_report.overall_severity == "CRITICAL":
            return "CRITICAL"
        
        if critical_bottlenecks or critical_recommendations:
            return "CRITICAL"
        
        # Check for high severity issues
        high_bottlenecks = [b for b in bottlenecks if b.severity == "HIGH"]
        high_recommendations = [r for r in recommendations if r.priority == "HIGH"]
        
        if regression_report and regression_report.overall_severity == "HIGH":
            return "POOR"
        
        if len(high_bottlenecks) > 2 or len(high_recommendations) > 2:
            return "POOR"
        
        # Check metrics
        if metrics.success_rate < 0.8 or metrics.safety_score < 0.8:
            return "POOR"
        
        if metrics.success_rate < 0.9 or metrics.safety_score < 0.9:
            return "FAIR"
        
        # Check for medium issues
        if len(bottlenecks) > 0 or len(recommendations) > 0:
            return "GOOD"
        
        return "EXCELLENT"
    
    def _identify_priority_actions(
        self,
        bottlenecks: List[BottleneckInfo],
        recommendations: List[Recommendation],
        regression_report: Optional[RegressionReport]
    ) -> tuple[bool, List[str]]:
        """Identify priority actions required."""
        actions = []
        
        # Critical bottlenecks
        critical_bottlenecks = [b for b in bottlenecks if b.severity == "CRITICAL"]
        if critical_bottlenecks:
            actions.append(
                f"Address {len(critical_bottlenecks)} critical bottleneck(s) immediately"
            )
        
        # Critical recommendations
        critical_recs = [r for r in recommendations if r.priority == "CRITICAL"]
        if critical_recs:
            for rec in critical_recs[:3]:  # Top 3
                actions.append(rec.title)
        
        # Critical regressions
        if regression_report and regression_report.overall_severity == "CRITICAL":
            actions.append(regression_report.recommendation)
        
        action_required = len(actions) > 0
        return action_required, actions
    
    def _determine_winner(
        self,
        analysis_a: ImprovementAnalysis,
        analysis_b: ImprovementAnalysis
    ) -> str:
        """Determine which execution performed better."""
        health_order = {"EXCELLENT": 5, "GOOD": 4, "FAIR": 3, "POOR": 2, "CRITICAL": 1}
        
        score_a = health_order.get(analysis_a.overall_health, 0)
        score_b = health_order.get(analysis_b.overall_health, 0)
        
        if score_a > score_b:
            return "execution_a"
        elif score_b > score_a:
            return "execution_b"
        else:
            # Compare metrics
            if analysis_a.metrics.success_rate > analysis_b.metrics.success_rate:
                return "execution_a"
            elif analysis_b.metrics.success_rate > analysis_a.metrics.success_rate:
                return "execution_b"
            else:
                return "tie"
    
    def _generate_health_recommendation(
        self,
        health: str,
        critical_count: int,
        high_count: int,
        unresolved_count: int
    ) -> str:
        """Generate health-based recommendation."""
        if health == "CRITICAL":
            return (
                f"URGENT: {critical_count} critical regression(s) detected. "
                "Immediate investigation and rollback may be required."
            )
        elif health == "POOR":
            return (
                f"WARNING: {high_count} high-severity regression(s) detected. "
                "Schedule investigation and remediation."
            )
        elif health == "FAIR":
            return (
                f"ATTENTION: {unresolved_count} unresolved regression(s). "
                "Monitor closely and address if trend continues."
            )
        elif health == "GOOD":
            return "Performance is stable with minor issues. Continue monitoring."
        else:
            return "Performance is excellent. No action required."
    
    def _count_severity_distribution(self, history: List) -> Dict[str, int]:
        """Count severity distribution in history."""
        distribution = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for event in history:
            severity = event.severity
            if severity in distribution:
                distribution[severity] += 1
        
        return distribution
