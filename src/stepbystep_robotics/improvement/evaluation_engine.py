"""
Evaluation Engine for analyzing robot performance and identifying improvement opportunities.

This module implements the EvaluationEngine component which analyzes execution traces
to compute metrics, compare executions, identify bottlenecks, and generate improvement
recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from ..models import (
    ExecutionTrace,
    PerformanceMetrics,
    StepMetrics,
    StepStatus,
)


@dataclass
class BottleneckInfo:
    """Information about a performance bottleneck."""
    step_id: str
    issue_type: str  # "SLOW", "HIGH_RETRY", "HIGH_DEVIATION"
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    metric_value: float
    description: str
    impact: str


@dataclass
class Recommendation:
    """Improvement recommendation based on performance analysis."""
    category: str  # "PERFORMANCE", "RELIABILITY", "EFFICIENCY", "SAFETY"
    priority: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    title: str
    description: str
    expected_improvement: str
    affected_steps: List[str] = field(default_factory=list)


@dataclass
class ComparisonReport:
    """Report comparing two execution traces."""
    execution_a_id: str
    execution_b_id: str
    duration_delta: float  # seconds
    duration_delta_percent: float
    success_rate_delta: float
    energy_delta: float
    accuracy_delta: float
    step_comparisons: Dict[str, Dict[str, float]]
    summary: str


class EvaluationEngine:
    """
    Analyzes robot performance and identifies improvement opportunities.
    
    The EvaluationEngine is the feedback loop that enables continuous improvement
    by computing metrics, comparing executions, identifying bottlenecks, and
    generating actionable recommendations.
    
    Requirements:
        - 7.1: Compute performance metrics from execution traces
        - 7.6: Generate actionable improvement recommendations
    """
    
    def __init__(self):
        """Initialize the evaluation engine."""
        pass
    
    def evaluateExecution(self, trace: ExecutionTrace) -> PerformanceMetrics:
        """
        Compute performance metrics from an execution trace.
        
        This method analyzes a complete execution trace and computes comprehensive
        performance metrics including duration, success rate, energy consumption,
        and various quality scores.
        
        Args:
            trace: Complete execution trace to analyze
        
        Returns:
            PerformanceMetrics with computed values
        
        Requirements:
            - 7.1: Compute performance metrics including duration, success rate, energy, accuracy
            - 7.2: Total duration equals sum of step durations plus gaps
            - 7.3: Success rate reflects actual ratio of successful steps
            - 7.4: All scores are in [0.0, 1.0] range
            - 7.5: Energy consumed is non-negative
            - 17.1: Total duration equals sum of step durations plus gaps
            - 17.2: Success rate equals ratio of successful steps to total steps
            - 17.3: All score metrics normalized to [0.0, 1.0]
            - 17.4: Energy consumed is non-negative
            - 17.5: Step metrics exist for all executed steps
        """
        # Compute total duration (Requirement 7.2, 17.1)
        if trace.end_time and trace.start_time:
            total_duration = (trace.end_time - trace.start_time).total_seconds()
        else:
            total_duration = 0.0
        
        # Compute success rate (Requirement 7.3, 17.2)
        if len(trace.steps) > 0:
            successful_steps = sum(1 for step in trace.steps if step.status == StepStatus.COMPLETED)
            success_rate = successful_steps / len(trace.steps)
        else:
            success_rate = 0.0
        
        # Compute energy consumed (Requirement 7.5, 17.4)
        if len(trace.state_history) >= 2:
            initial_battery = trace.state_history[0].battery_level
            final_battery = trace.state_history[-1].battery_level
            energy_consumed = max(0.0, initial_battery - final_battery)
        else:
            energy_consumed = 0.0
        
        # Compute accuracy score (Requirement 7.4, 17.3)
        if len(trace.steps) > 0:
            total_deviations = sum(len(step.deviations) for step in trace.steps)
            # Fewer deviations = higher accuracy
            accuracy_score = max(0.0, 1.0 - (total_deviations / (len(trace.steps) * 2)))
        else:
            accuracy_score = 1.0
        
        # Compute smoothness score (Requirement 7.4, 17.3)
        if len(trace.steps) > 1:
            # Check if step durations are consistent
            durations = [step.actual_duration for step in trace.steps]
            avg_duration = sum(durations) / len(durations)
            variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
            # Lower variance = higher smoothness
            smoothness_score = max(0.0, 1.0 - min(1.0, variance / (avg_duration ** 2 + 0.01)))
        else:
            smoothness_score = 1.0
        
        # Compute safety score (Requirement 7.4, 17.3)
        critical_anomalies = sum(1 for a in trace.anomalies if a.severity == "CRITICAL")
        warning_anomalies = sum(1 for a in trace.anomalies if a.severity == "WARNING")
        safety_score = max(0.0, 1.0 - (critical_anomalies * 0.3 + warning_anomalies * 0.1))
        
        # Compute step metrics (Requirement 17.5)
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
    
    def compareExecutions(
        self,
        trace_a: ExecutionTrace,
        trace_b: ExecutionTrace
    ) -> ComparisonReport:
        """
        Compare two execution traces to identify performance variations.
        
        This method performs a detailed comparison of two executions of the same
        or similar tasks, highlighting differences in performance metrics and
        identifying which execution performed better in various aspects.
        
        Args:
            trace_a: First execution trace
            trace_b: Second execution trace
        
        Returns:
            ComparisonReport with detailed comparison results
        
        Requirements:
            - 7.6: Identify performance variations between executions
        """
        # Compute metrics for both traces
        metrics_a = self.evaluateExecution(trace_a)
        metrics_b = self.evaluateExecution(trace_b)
        
        # Compute deltas
        duration_delta = metrics_b.total_duration - metrics_a.total_duration
        duration_delta_percent = (
            (duration_delta / metrics_a.total_duration * 100)
            if metrics_a.total_duration > 0 else 0.0
        )
        
        success_rate_delta = metrics_b.success_rate - metrics_a.success_rate
        energy_delta = metrics_b.energy_consumed - metrics_a.energy_consumed
        accuracy_delta = metrics_b.accuracy_score - metrics_a.accuracy_score
        
        # Compare step-by-step
        step_comparisons = {}
        for step_id in metrics_a.step_metrics:
            if step_id in metrics_b.step_metrics:
                step_a = metrics_a.step_metrics[step_id]
                step_b = metrics_b.step_metrics[step_id]
                
                step_comparisons[step_id] = {
                    'duration_delta': step_b.duration - step_a.duration,
                    'retry_count_delta': step_b.retry_count - step_a.retry_count,
                    'error_rate_delta': step_b.error_rate - step_a.error_rate,
                }
        
        # Generate summary
        summary_parts = []
        
        if abs(duration_delta_percent) > 10:
            direction = "slower" if duration_delta > 0 else "faster"
            summary_parts.append(
                f"Execution B is {abs(duration_delta_percent):.1f}% {direction} than A"
            )
        
        if abs(success_rate_delta) > 0.1:
            direction = "higher" if success_rate_delta > 0 else "lower"
            summary_parts.append(
                f"Success rate is {abs(success_rate_delta * 100):.1f}% {direction}"
            )
        
        if abs(energy_delta) > 0.05:
            direction = "more" if energy_delta > 0 else "less"
            summary_parts.append(
                f"Energy consumption is {abs(energy_delta * 100):.1f}% {direction}"
            )
        
        if not summary_parts:
            summary = "Executions have similar performance characteristics"
        else:
            summary = "; ".join(summary_parts)
        
        return ComparisonReport(
            execution_a_id=trace_a.execution_id,
            execution_b_id=trace_b.execution_id,
            duration_delta=duration_delta,
            duration_delta_percent=duration_delta_percent,
            success_rate_delta=success_rate_delta,
            energy_delta=energy_delta,
            accuracy_delta=accuracy_delta,
            step_comparisons=step_comparisons,
            summary=summary
        )
    
    def identifyBottlenecks(self, trace: ExecutionTrace) -> List[BottleneckInfo]:
        """
        Identify performance bottlenecks in an execution trace.
        
        This method analyzes the execution trace to find steps that are
        significantly slower, have high retry counts, or exhibit high
        deviation rates - all indicators of potential bottlenecks.
        
        Args:
            trace: Execution trace to analyze
        
        Returns:
            List of identified bottlenecks, sorted by severity
        
        Requirements:
            - 7.6: Identify bottlenecks and inefficiencies in robot behavior
        """
        bottlenecks = []
        
        if not trace.steps:
            return bottlenecks
        
        # Compute metrics for analysis
        metrics = self.evaluateExecution(trace)
        
        # Calculate average step duration
        durations = [step.actual_duration for step in trace.steps]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Identify slow steps (>2x average duration)
        for step in trace.steps:
            if avg_duration > 0 and step.actual_duration > 2 * avg_duration:
                severity = "CRITICAL" if step.actual_duration > 4 * avg_duration else "HIGH"
                bottlenecks.append(BottleneckInfo(
                    step_id=step.step_id,
                    issue_type="SLOW",
                    severity=severity,
                    metric_value=step.actual_duration,
                    description=f"Step takes {step.actual_duration:.2f}s (avg: {avg_duration:.2f}s)",
                    impact=f"Contributes {(step.actual_duration / metrics.total_duration * 100):.1f}% of total execution time"
                ))
        
        # Identify high retry steps
        for step in trace.steps:
            if step.retry_count > 2:
                severity = "CRITICAL" if step.retry_count > 5 else "HIGH"
                bottlenecks.append(BottleneckInfo(
                    step_id=step.step_id,
                    issue_type="HIGH_RETRY",
                    severity=severity,
                    metric_value=float(step.retry_count),
                    description=f"Step required {step.retry_count} retries",
                    impact="Indicates unreliable execution or incorrect preconditions"
                ))
        
        # Identify high deviation steps
        for step in trace.steps:
            if len(step.deviations) > 3:
                severity = "HIGH" if len(step.deviations) > 5 else "MEDIUM"
                bottlenecks.append(BottleneckInfo(
                    step_id=step.step_id,
                    issue_type="HIGH_DEVIATION",
                    severity=severity,
                    metric_value=float(len(step.deviations)),
                    description=f"Step has {len(step.deviations)} deviations from expected behavior",
                    impact="May indicate control issues or environmental interference"
                ))
        
        # Sort by severity (CRITICAL > HIGH > MEDIUM > LOW)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        bottlenecks.sort(key=lambda b: severity_order.get(b.severity, 4))
        
        return bottlenecks
    
    def generateRecommendations(
        self,
        metrics: PerformanceMetrics,
        trace: Optional[ExecutionTrace] = None
    ) -> List[Recommendation]:
        """
        Generate actionable improvement recommendations based on performance metrics.
        
        This method analyzes performance metrics and optionally the full trace
        to generate specific, actionable recommendations for improving robot
        performance, reliability, efficiency, and safety.
        
        Args:
            metrics: Performance metrics to analyze
            trace: Optional execution trace for detailed analysis
        
        Returns:
            List of recommendations, sorted by priority
        
        Requirements:
            - 7.6: Generate actionable improvement recommendations
        """
        recommendations = []
        
        # Performance recommendations
        if metrics.total_duration > 60:  # More than 1 minute
            recommendations.append(Recommendation(
                category="PERFORMANCE",
                priority="HIGH",
                title="Optimize execution duration",
                description=f"Total execution time is {metrics.total_duration:.1f}s. Consider parallelizing independent steps or optimizing slow operations.",
                expected_improvement="20-40% reduction in execution time"
            ))
        
        # Reliability recommendations
        if metrics.success_rate < 0.9:
            priority = "CRITICAL" if metrics.success_rate < 0.7 else "HIGH"
            recommendations.append(Recommendation(
                category="RELIABILITY",
                priority=priority,
                title="Improve task success rate",
                description=f"Success rate is {metrics.success_rate * 100:.1f}%. Review failed steps and adjust preconditions or add retry logic.",
                expected_improvement=f"Target: >90% success rate (current: {metrics.success_rate * 100:.1f}%)"
            ))
        
        # Efficiency recommendations
        if metrics.energy_consumed > 0.3:  # More than 30% battery drain
            recommendations.append(Recommendation(
                category="EFFICIENCY",
                priority="MEDIUM",
                title="Reduce energy consumption",
                description=f"Task consumes {metrics.energy_consumed * 100:.1f}% battery. Optimize motion paths and reduce unnecessary movements.",
                expected_improvement="15-25% reduction in energy usage"
            ))
        
        # Accuracy recommendations
        if metrics.accuracy_score < 0.8:
            recommendations.append(Recommendation(
                category="PERFORMANCE",
                priority="HIGH",
                title="Improve execution accuracy",
                description=f"Accuracy score is {metrics.accuracy_score:.2f}. High deviation count indicates control or calibration issues.",
                expected_improvement="Reduce deviations by 30-50%"
            ))
        
        # Safety recommendations
        if metrics.safety_score < 0.9:
            priority = "CRITICAL" if metrics.safety_score < 0.7 else "HIGH"
            recommendations.append(Recommendation(
                category="SAFETY",
                priority=priority,
                title="Address safety concerns",
                description=f"Safety score is {metrics.safety_score:.2f}. Review anomalies and strengthen safety constraints.",
                expected_improvement="Eliminate critical anomalies, reduce warnings"
            ))
        
        # Smoothness recommendations
        if metrics.smoothness_score < 0.7:
            recommendations.append(Recommendation(
                category="PERFORMANCE",
                priority="MEDIUM",
                title="Improve execution smoothness",
                description=f"Smoothness score is {metrics.smoothness_score:.2f}. High timing variance indicates inconsistent performance.",
                expected_improvement="More predictable execution times"
            ))
        
        # Trace-specific recommendations
        if trace:
            bottlenecks = self.identifyBottlenecks(trace)
            
            # Recommend addressing critical bottlenecks
            critical_bottlenecks = [b for b in bottlenecks if b.severity == "CRITICAL"]
            if critical_bottlenecks:
                affected_steps = [b.step_id for b in critical_bottlenecks]
                recommendations.append(Recommendation(
                    category="PERFORMANCE",
                    priority="CRITICAL",
                    title="Address critical bottlenecks",
                    description=f"Found {len(critical_bottlenecks)} critical bottlenecks. Focus optimization efforts on these steps.",
                    expected_improvement="40-60% improvement in overall execution time",
                    affected_steps=affected_steps
                ))
            
            # Recommend retry logic improvements
            high_retry_steps = [
                step.step_id for step in trace.steps
                if step.retry_count > 3
            ]
            if high_retry_steps:
                recommendations.append(Recommendation(
                    category="RELIABILITY",
                    priority="HIGH",
                    title="Optimize retry-prone steps",
                    description=f"{len(high_retry_steps)} steps require frequent retries. Review preconditions and add validation.",
                    expected_improvement="Reduce retry count by 50-70%",
                    affected_steps=high_retry_steps
                ))
        
        # Sort by priority (CRITICAL > HIGH > MEDIUM > LOW)
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 4))
        
        return recommendations
