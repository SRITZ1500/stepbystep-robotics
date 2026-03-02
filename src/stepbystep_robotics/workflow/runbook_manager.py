"""
Runbook Manager for StepbyStep:ROBOTICS

Manages operational procedures and task specifications for robot operations.
Provides runbook creation, validation, execution coordination, and usage tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4


@dataclass
class RunbookStep:
    """A single step in a runbook"""
    step_number: int
    task_id: str
    description: str
    parameters: Dict[str, any] = field(default_factory=dict)
    dependencies: Set[int] = field(default_factory=set)  # Step numbers this depends on
    optional: bool = False
    timeout_seconds: Optional[int] = None


@dataclass
class Runbook:
    """Operational runbook definition"""
    runbook_id: UUID
    name: str
    description: str
    version: int
    steps: List[RunbookStep]
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    tags: Set[str] = field(default_factory=set)
    
    def validate_structure(self) -> tuple[bool, List[str]]:
        """
        Validate runbook structure and dependencies.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Check for empty steps
        if not self.steps:
            errors.append("Runbook must have at least one step")
            return False, errors
        
        # Check step numbers are sequential
        step_numbers = [step.step_number for step in self.steps]
        expected_numbers = list(range(1, len(self.steps) + 1))
        if step_numbers != expected_numbers:
            errors.append(f"Step numbers must be sequential starting from 1, got {step_numbers}")
        
        # Check for circular dependencies
        for step in self.steps:
            if step.step_number in step.dependencies:
                errors.append(f"Step {step.step_number} cannot depend on itself")
            
            # Check dependencies reference valid steps
            for dep in step.dependencies:
                if dep >= step.step_number:
                    errors.append(f"Step {step.step_number} cannot depend on step {dep} (must depend on earlier steps)")
                if dep < 1 or dep > len(self.steps):
                    errors.append(f"Step {step.step_number} has invalid dependency {dep}")
        
        # Check for circular dependency chains
        if self._has_circular_dependencies():
            errors.append("Runbook contains circular dependencies")
        
        return len(errors) == 0, errors
    
    def _has_circular_dependencies(self) -> bool:
        """Check for circular dependencies using topological sort"""
        # Build adjacency list
        graph = {step.step_number: list(step.dependencies) for step in self.steps}
        
        # Track visited nodes
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: int) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step in self.steps:
            if step.step_number not in visited:
                if has_cycle(step.step_number):
                    return True
        
        return False


@dataclass
class RunbookExecution:
    """Record of a runbook execution"""
    execution_id: UUID
    runbook_id: UUID
    runbook_version: int
    robot_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "IN_PROGRESS"  # IN_PROGRESS, COMPLETED, FAILED, ABORTED
    completed_steps: Set[int] = field(default_factory=set)
    failed_steps: Set[int] = field(default_factory=set)
    skipped_steps: Set[int] = field(default_factory=set)
    execution_traces: Dict[int, UUID] = field(default_factory=dict)  # step_number -> trace_id


@dataclass
class RunbookUsageStats:
    """Usage statistics for a runbook"""
    runbook_id: UUID
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_duration_seconds: float = 0.0
    last_executed: Optional[datetime] = None
    success_rate: float = 0.0


class RunbookManager:
    """
    Manages operational runbooks for robot operations.
    
    Responsibilities:
    - Store and version control operational runbooks
    - Validate runbook structure and dependencies
    - Coordinate runbook execution with task specifications
    - Track runbook usage patterns and success rates
    """
    
    def __init__(self):
        self.runbooks: Dict[UUID, Runbook] = {}
        self.runbook_versions: Dict[UUID, List[Runbook]] = {}  # runbook_id -> list of versions
        self.executions: Dict[UUID, RunbookExecution] = {}
        self.usage_stats: Dict[UUID, RunbookUsageStats] = {}
        self.task_registry: Set[str] = set()  # Track valid task IDs
    
    def register_task(self, task_id: str) -> None:
        """Register a valid task ID"""
        self.task_registry.add(task_id)
    
    def create_runbook(self, name: str, description: str, steps: List[RunbookStep],
                      created_by: str, tags: Optional[Set[str]] = None) -> UUID:
        """
        Create a new runbook with version control.
        
        Preconditions:
        - name is non-empty
        - steps is non-empty
        - All referenced tasks exist in registry
        
        Postconditions:
        - Returns unique RunbookId
        - Runbook is stored with version 1
        - Runbook structure is validated
        
        Requirements:
        - 10.1: Assign unique RunbookId and store with version control
        - 10.2: Validate structure and dependencies before accepting
        """
        if not name:
            raise ValueError("Runbook name cannot be empty")
        
        if not steps:
            raise ValueError("Runbook must have at least one step")
        
        runbook_id = uuid4()
        now = datetime.utcnow()
        
        runbook = Runbook(
            runbook_id=runbook_id,
            name=name,
            description=description,
            version=1,
            steps=steps,
            created_at=now,
            created_by=created_by,
            updated_at=now,
            updated_by=created_by,
            tags=tags or set()
        )
        
        # Validate structure
        is_valid, errors = runbook.validate_structure()
        if not is_valid:
            raise ValueError(f"Invalid runbook structure: {'; '.join(errors)}")
        
        # Validate all referenced tasks exist
        validation_result = self.validate_runbook(runbook)
        if not validation_result.is_valid:
            raise ValueError(f"Runbook validation failed: {'; '.join(validation_result.errors)}")
        
        # Store runbook
        self.runbooks[runbook_id] = runbook
        self.runbook_versions[runbook_id] = [runbook]
        
        # Initialize usage stats
        self.usage_stats[runbook_id] = RunbookUsageStats(runbook_id=runbook_id)
        
        return runbook_id
    
    def get_runbook(self, runbook_id: UUID, version: Optional[int] = None) -> Optional[Runbook]:
        """
        Get a runbook by ID and optional version.
        
        Args:
            runbook_id: The runbook ID
            version: Optional version number (defaults to latest)
        
        Returns:
            Runbook if found, None otherwise
        """
        if runbook_id not in self.runbooks:
            return None
        
        if version is None:
            return self.runbooks[runbook_id]
        
        # Find specific version
        versions = self.runbook_versions.get(runbook_id, [])
        for rb in versions:
            if rb.version == version:
                return rb
        
        return None
    
    def update_runbook(self, runbook_id: UUID, updates: Dict[str, any],
                      updated_by: str) -> Runbook:
        """
        Update a runbook and create a new version.
        
        Preconditions:
        - runbook_id exists
        - updates are valid
        
        Postconditions:
        - New version is created
        - Previous versions are preserved
        - Structure is validated before accepting
        
        Requirements:
        - 10.2: Validate structure and dependencies before accepting changes
        """
        if runbook_id not in self.runbooks:
            raise ValueError(f"Runbook {runbook_id} not found")
        
        current = self.runbooks[runbook_id]
        now = datetime.utcnow()
        
        # Create new version with updates
        new_version = Runbook(
            runbook_id=runbook_id,
            name=updates.get('name', current.name),
            description=updates.get('description', current.description),
            version=current.version + 1,
            steps=updates.get('steps', current.steps),
            created_at=current.created_at,
            created_by=current.created_by,
            updated_at=now,
            updated_by=updated_by,
            tags=updates.get('tags', current.tags)
        )
        
        # Validate structure
        is_valid, errors = new_version.validate_structure()
        if not is_valid:
            raise ValueError(f"Invalid runbook structure: {'; '.join(errors)}")
        
        # Validate all referenced tasks exist
        validation_result = self.validate_runbook(new_version)
        if not validation_result.is_valid:
            raise ValueError(f"Runbook validation failed: {'; '.join(validation_result.errors)}")
        
        # Store new version
        self.runbooks[runbook_id] = new_version
        self.runbook_versions[runbook_id].append(new_version)
        
        return new_version
    
    def execute_runbook(self, runbook_id: UUID, robot_id: UUID,
                       parameters: Optional[Dict[str, any]] = None) -> UUID:
        """
        Start execution of a runbook.
        
        This method initializes execution tracking. Actual task execution
        is coordinated with the Task_Spec_Engine.
        
        Preconditions:
        - runbook_id exists
        - robot_id is valid
        
        Postconditions:
        - Returns unique execution_id
        - Execution is tracked in system
        - Usage stats are updated
        
        Requirements:
        - 10.3: Coordinate with Task_Spec_Engine to execute runbook steps
        - 10.4: Track runbook usage patterns and success rates
        """
        if runbook_id not in self.runbooks:
            raise ValueError(f"Runbook {runbook_id} not found")
        
        runbook = self.runbooks[runbook_id]
        execution_id = uuid4()
        
        execution = RunbookExecution(
            execution_id=execution_id,
            runbook_id=runbook_id,
            runbook_version=runbook.version,
            robot_id=robot_id,
            started_at=datetime.utcnow()
        )
        
        self.executions[execution_id] = execution
        
        # Update usage stats
        stats = self.usage_stats[runbook_id]
        stats.total_executions += 1
        stats.last_executed = execution.started_at
        
        return execution_id
    
    def record_step_completion(self, execution_id: UUID, step_number: int,
                              trace_id: UUID, success: bool) -> None:
        """Record completion of a runbook step"""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution = self.executions[execution_id]
        execution.execution_traces[step_number] = trace_id
        
        if success:
            execution.completed_steps.add(step_number)
        else:
            execution.failed_steps.add(step_number)
    
    def record_step_skipped(self, execution_id: UUID, step_number: int) -> None:
        """Record that a step was skipped"""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution = self.executions[execution_id]
        execution.skipped_steps.add(step_number)
    
    def complete_execution(self, execution_id: UUID, status: str) -> None:
        """Mark a runbook execution as complete"""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution = self.executions[execution_id]
        execution.completed_at = datetime.utcnow()
        execution.status = status
        
        # Update usage stats
        stats = self.usage_stats[execution.runbook_id]
        
        if status == "COMPLETED":
            stats.successful_executions += 1
        elif status in ["FAILED", "ABORTED"]:
            stats.failed_executions += 1
        
        # Update success rate
        if stats.total_executions > 0:
            stats.success_rate = stats.successful_executions / stats.total_executions
        
        # Update average duration
        if execution.completed_at:
            duration = (execution.completed_at - execution.started_at).total_seconds()
            if stats.average_duration_seconds == 0:
                stats.average_duration_seconds = duration
            else:
                # Running average
                total = stats.total_executions
                stats.average_duration_seconds = (
                    (stats.average_duration_seconds * (total - 1) + duration) / total
                )
    
    def validate_runbook(self, runbook: Runbook) -> 'ValidationReport':
        """
        Validate a runbook's structure and dependencies.
        
        Postconditions:
        - Returns validation report with errors if any
        - Checks all referenced tasks exist
        - Validates step dependencies
        
        Requirements:
        - 10.5: Ensure all referenced tasks and dependencies exist
        """
        errors = []
        
        # Validate structure
        is_valid, structure_errors = runbook.validate_structure()
        errors.extend(structure_errors)
        
        # Validate all referenced tasks exist
        for step in runbook.steps:
            if step.task_id not in self.task_registry:
                errors.append(f"Step {step.step_number} references unknown task '{step.task_id}'")
        
        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    def get_usage_stats(self, runbook_id: UUID) -> Optional[RunbookUsageStats]:
        """Get usage statistics for a runbook"""
        return self.usage_stats.get(runbook_id)
    
    def list_runbooks(self, tags: Optional[Set[str]] = None) -> List[Runbook]:
        """
        List all runbooks, optionally filtered by tags.
        
        Args:
            tags: Optional set of tags to filter by
        
        Returns:
            List of runbooks matching the filter
        """
        runbooks = list(self.runbooks.values())
        
        if tags:
            runbooks = [rb for rb in runbooks if rb.tags & tags]
        
        return sorted(runbooks, key=lambda rb: rb.name)
    
    def get_execution(self, execution_id: UUID) -> Optional[RunbookExecution]:
        """Get execution details by ID"""
        return self.executions.get(execution_id)
    
    def list_executions(self, runbook_id: Optional[UUID] = None,
                       robot_id: Optional[UUID] = None,
                       status: Optional[str] = None) -> List[RunbookExecution]:
        """
        List executions with optional filters.
        
        Args:
            runbook_id: Filter by runbook
            robot_id: Filter by robot
            status: Filter by status
        
        Returns:
            List of matching executions
        """
        executions = list(self.executions.values())
        
        if runbook_id:
            executions = [e for e in executions if e.runbook_id == runbook_id]
        
        if robot_id:
            executions = [e for e in executions if e.robot_id == robot_id]
        
        if status:
            executions = [e for e in executions if e.status == status]
        
        return sorted(executions, key=lambda e: e.started_at, reverse=True)


@dataclass
class ValidationReport:
    """Result of runbook validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
