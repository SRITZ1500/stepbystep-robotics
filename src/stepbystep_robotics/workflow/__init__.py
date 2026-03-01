"""
Workflow Layer - Enables operability through runbooks, task specifications, and execution tracking.
"""

from .task_spec_engine import TaskSpecEngine, ValidationResult

__all__ = ['TaskSpecEngine', 'ValidationResult']
