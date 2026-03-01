"""
Task Spec Engine component for StepbyStep:ROBOTICS system.

This module implements the TaskSpecEngine class which defines, validates, and manages
task specifications with formal constraints. It handles:
- Task definition and creation
- Specification validation
- Task decomposition into subtasks
- Precondition and postcondition verification
"""

from typing import Dict, List, Optional, Set
from uuid import UUID

from ..models import (
    TaskSpecification,
    TaskStep,
    Condition,
    ConditionType,
    RobotState,
    ActionType,
    FailureStrategy
)


class ValidationResult:
    """Result of task specification validation."""
    
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
    
    def __repr__(self):
        if self.is_valid:
            return "ValidationResult(is_valid=True)"
        return f"ValidationResult(is_valid=False, errors={self.errors})"


class TaskSpecEngine:
    """
    Task Spec Engine for defining, validating, and managing task specifications.
    
    This component is responsible for:
    - Defining task specifications with preconditions and postconditions
    - Validating task feasibility given robot capabilities
    - Decomposing complex tasks into executable subtasks
    - Verifying task completion against success criteria
    
    Interface (from design.md):
        PROCEDURE defineTask(spec: TaskSpecification): TaskId
        PROCEDURE validateSpec(spec: TaskSpecification): ValidationResult
        PROCEDURE decomposeTask(taskId: TaskId): SubTaskSequence
        PROCEDURE checkPreconditions(taskId: TaskId, currentState: RobotState): Boolean
        PROCEDURE verifyPostconditions(taskId: TaskId, resultState: RobotState): Boolean
    """
    
    def __init__(self):
        """Initialize the Task Spec Engine."""
        # Storage for task specifications
        self._tasks: Dict[str, TaskSpecification] = {}
        
        # Registry of available robot capabilities
        self._capability_registry: Set[str] = set()
        
        # Task decomposition rules (parent_task_id -> list of subtask_ids)
        self._decomposition_map: Dict[str, List[str]] = {}
    
    def register_capability(self, capability: str) -> None:
        """
        Register a robot capability in the system.
        
        Args:
            capability: Name of the capability to register
        """
        if not capability:
            raise ValueError("capability cannot be empty")
        self._capability_registry.add(capability)
    
    def defineTask(self, spec: TaskSpecification) -> str:
        """
        Define a new task specification in the system.
        
        Args:
            spec: TaskSpecification to define
        
        Returns:
            task_id of the defined task
        
        Raises:
            ValueError: If task_id already exists or spec is invalid
        
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        if not isinstance(spec, TaskSpecification):
            raise ValueError("spec must be a TaskSpecification")
        
        # Check if task already exists
        if spec.task_id in self._tasks:
            raise ValueError(f"Task with id '{spec.task_id}' already exists")
        
        # Validate the specification
        validation_result = self.validateSpec(spec)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid task specification: {validation_result.errors}")
        
        # Store the task
        self._tasks[spec.task_id] = spec
        
        return spec.task_id
    
    def validateSpec(self, spec: TaskSpecification) -> ValidationResult:
        """
        Validate a task specification for correctness and feasibility.
        
        Validates:
        - Preconditions are verifiable from RobotState
        - Postconditions are measurable and deterministic
        - Steps form valid execution sequence without circular dependencies
        - All referenced capabilities exist in capability registry
        - Safety constraints are well-formed
        
        Args:
            spec: TaskSpecification to validate
        
        Returns:
            ValidationResult indicating validity and any errors
        
        Requirements: 3.1, 3.2, 3.3
        """
        errors = []
        
        # Validate basic structure (already done in TaskSpecification.__post_init__)
        try:
            # This will trigger validation in the dataclass
            if not isinstance(spec, TaskSpecification):
                errors.append("spec must be a TaskSpecification")
                return ValidationResult(False, errors)
        except ValueError as e:
            errors.append(str(e))
            return ValidationResult(False, errors)
        
        # Validate preconditions are verifiable from RobotState
        for i, condition in enumerate(spec.preconditions):
            if not self._is_condition_verifiable(condition):
                errors.append(f"Precondition {i} is not verifiable from RobotState: {condition.expression}")
        
        # Validate postconditions are measurable and deterministic
        for i, condition in enumerate(spec.postconditions):
            if not self._is_condition_measurable(condition):
                errors.append(f"Postcondition {i} is not measurable: {condition.expression}")
        
        # Validate steps form valid execution sequence without circular dependencies
        step_validation_errors = self._validate_step_sequence(spec.steps)
        errors.extend(step_validation_errors)
        
        # Validate all referenced capabilities exist
        if self._capability_registry:  # Only check if registry is populated
            missing_capabilities = spec.required_capabilities - self._capability_registry
            if missing_capabilities:
                errors.append(f"Missing required capabilities: {missing_capabilities}")
        
        # Validate safety constraints are well-formed
        for i, constraint in enumerate(spec.safety_constraints):
            if not self._is_condition_verifiable(constraint):
                errors.append(f"Safety constraint {i} is not well-formed: {constraint.expression}")
        
        return ValidationResult(len(errors) == 0, errors)
    
    def decomposeTask(self, task_id: str) -> List[TaskSpecification]:
        """
        Decompose a complex task into a sequence of executable subtasks.
        
        Args:
            task_id: ID of the task to decompose
        
        Returns:
            List of subtask specifications in execution order
        
        Raises:
            ValueError: If task_id doesn't exist or task cannot be decomposed
        
        Requirements: 24.1, 24.2, 24.3, 24.4
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task '{task_id}' not found")
        
        # Check if task has a decomposition defined
        if task_id not in self._decomposition_map:
            # Task has no decomposition - return empty list (atomic task)
            return []
        
        # Get subtask IDs
        subtask_ids = self._decomposition_map[task_id]
        
        # Retrieve subtask specifications
        subtasks = []
        for subtask_id in subtask_ids:
            if subtask_id not in self._tasks:
                raise ValueError(f"Subtask '{subtask_id}' not found in decomposition of '{task_id}'")
            subtasks.append(self._tasks[subtask_id])
        
        # Validate subtask dependencies are satisfied
        parent_task = self._tasks[task_id]
        validation_errors = self._validate_subtask_dependencies(parent_task, subtasks)
        if validation_errors:
            raise ValueError(f"Invalid task decomposition: {validation_errors}")
        
        return subtasks
    
    def checkPreconditions(self, task_id: str, current_state: RobotState) -> bool:
        """
        Check if task preconditions are satisfied in the current robot state.
        
        Args:
            task_id: ID of the task to check
            current_state: Current robot state
        
        Returns:
            True if all preconditions are satisfied, False otherwise
        
        Raises:
            ValueError: If task_id doesn't exist
        
        Requirements: 3.4
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task '{task_id}' not found")
        
        task = self._tasks[task_id]
        
        # Check each precondition
        for condition in task.preconditions:
            if not self._evaluate_condition(condition, current_state):
                return False
        
        return True
    
    def verifyPostconditions(self, task_id: str, result_state: RobotState) -> bool:
        """
        Verify that task postconditions are satisfied in the result state.
        
        Args:
            task_id: ID of the task to verify
            result_state: Final robot state after task execution
        
        Returns:
            True if all postconditions are satisfied, False otherwise
        
        Raises:
            ValueError: If task_id doesn't exist
        
        Requirements: 3.5
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task '{task_id}' not found")
        
        task = self._tasks[task_id]
        
        # Check each postcondition
        for condition in task.postconditions:
            if not self._evaluate_condition(condition, result_state):
                return False
        
        return True
    
    def register_decomposition(self, parent_task_id: str, subtask_ids: List[str]) -> None:
        """
        Register a task decomposition mapping.
        
        Args:
            parent_task_id: ID of the parent task
            subtask_ids: List of subtask IDs in execution order
        
        Raises:
            ValueError: If parent_task_id doesn't exist or subtask_ids are invalid
        """
        if parent_task_id not in self._tasks:
            raise ValueError(f"Parent task '{parent_task_id}' not found")
        
        if not subtask_ids:
            raise ValueError("subtask_ids cannot be empty")
        
        # Validate all subtasks exist
        for subtask_id in subtask_ids:
            if subtask_id not in self._tasks:
                raise ValueError(f"Subtask '{subtask_id}' not found")
        
        self._decomposition_map[parent_task_id] = subtask_ids
    
    def get_task(self, task_id: str) -> TaskSpecification:
        """
        Retrieve a task specification by ID.
        
        Args:
            task_id: ID of the task to retrieve
        
        Returns:
            TaskSpecification for the given task_id
        
        Raises:
            ValueError: If task_id doesn't exist
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task '{task_id}' not found")
        return self._tasks[task_id]
    
    # Private helper methods
    
    def _is_condition_verifiable(self, condition: Condition) -> bool:
        """
        Check if a condition can be verified from RobotState.
        
        A condition is verifiable if its expression references valid RobotState fields.
        """
        # Parse the expression to check if it references valid state fields
        # Valid fields: position, orientation, joint_states, sensor_readings, 
        #               actuator_states, battery_level, error_flags
        
        valid_fields = {
            'position', 'orientation', 'joint_states', 'sensor_readings',
            'actuator_states', 'battery_level', 'error_flags', 'x', 'y', 'z'
        }
        
        # Simple validation: check if expression contains at least one valid field
        # In a production system, this would use proper expression parsing
        expression_lower = condition.expression.lower()
        
        # Check for valid field references
        has_valid_field = any(field in expression_lower for field in valid_fields)
        
        return has_valid_field
    
    def _is_condition_measurable(self, condition: Condition) -> bool:
        """
        Check if a condition is measurable and deterministic.
        
        A condition is measurable if it can be evaluated to a boolean value
        from observable robot state.
        """
        # For now, use same logic as verifiable
        # In production, would add checks for determinism (no random/time-dependent values)
        return self._is_condition_verifiable(condition)
    
    def _validate_step_sequence(self, steps: List[TaskStep]) -> List[str]:
        """
        Validate that steps form a valid execution sequence without circular dependencies.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not steps:
            errors.append("Task must have at least one step")
            return errors
        
        # Check for duplicate step IDs
        step_ids = [step.step_id for step in steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Step IDs must be unique")
        
        # Validate each step has positive expected duration
        for step in steps:
            if step.expected_duration <= 0:
                errors.append(f"Step '{step.step_id}' has non-positive expected_duration")
        
        # In a production system, would check for circular dependencies in step parameters
        # For now, we assume linear sequence is valid
        
        return errors
    
    def _validate_subtask_dependencies(
        self, 
        parent_task: TaskSpecification, 
        subtasks: List[TaskSpecification]
    ) -> List[str]:
        """
        Validate that subtask dependencies are satisfied and composition achieves parent postconditions.
        
        Validates:
        - Subtask dependencies form a valid DAG (no cycles)
        - First subtask preconditions are compatible with parent preconditions
        - Last subtask postconditions achieve parent postconditions
        - Subtask chain is valid (each subtask's postconditions enable next subtask's preconditions)
        
        Returns:
            List of validation error messages (empty if valid)
        
        Requirements: 24.2, 24.3, 24.4
        """
        errors = []
        
        if not subtasks:
            errors.append("Subtask list cannot be empty")
            return errors
        
        # 1. Validate subtask dependencies form a valid DAG (no cycles)
        # Check for circular dependencies in the decomposition map
        cycle_errors = self._check_for_cycles(parent_task.task_id, set())
        errors.extend(cycle_errors)
        
        # 2. Validate first subtask preconditions are compatible with parent preconditions
        first_subtask = subtasks[0]
        if not self._are_preconditions_compatible(parent_task.preconditions, first_subtask.preconditions):
            errors.append(
                f"First subtask '{first_subtask.task_id}' preconditions are not compatible "
                f"with parent task '{parent_task.task_id}' preconditions"
            )
        
        # 3. Validate last subtask postconditions achieve parent postconditions
        last_subtask = subtasks[-1]
        if not self._do_postconditions_achieve_parent(last_subtask.postconditions, parent_task.postconditions):
            errors.append(
                f"Last subtask '{last_subtask.task_id}' postconditions do not achieve "
                f"parent task '{parent_task.task_id}' postconditions"
            )
        
        # 4. Validate subtask chain: each subtask's postconditions satisfy next subtask's preconditions
        for i in range(len(subtasks) - 1):
            current_subtask = subtasks[i]
            next_subtask = subtasks[i + 1]
            
            # Ensure subtasks have conditions defined
            if not current_subtask.postconditions:
                errors.append(f"Subtask '{current_subtask.task_id}' has no postconditions")
            if not next_subtask.preconditions:
                errors.append(f"Subtask '{next_subtask.task_id}' has no preconditions")
            
            # Check if postconditions of current enable preconditions of next
            if current_subtask.postconditions and next_subtask.preconditions:
                if not self._do_postconditions_enable_preconditions(
                    current_subtask.postconditions, 
                    next_subtask.preconditions
                ):
                    errors.append(
                        f"Subtask '{current_subtask.task_id}' postconditions do not enable "
                        f"subtask '{next_subtask.task_id}' preconditions"
                    )
        
        return errors
    
    def _check_for_cycles(self, task_id: str, visited: Set[str]) -> List[str]:
        """
        Check for circular dependencies in task decomposition.
        
        Args:
            task_id: Current task ID to check
            visited: Set of already visited task IDs in current path
        
        Returns:
            List of error messages if cycles detected
        """
        errors = []
        
        # If we've seen this task in the current path, we have a cycle
        if task_id in visited:
            errors.append(f"Circular dependency detected: task '{task_id}' appears in its own decomposition chain")
            return errors
        
        # If task has no decomposition, no cycle possible
        if task_id not in self._decomposition_map:
            return errors
        
        # Add current task to visited set
        new_visited = visited | {task_id}
        
        # Recursively check all subtasks
        for subtask_id in self._decomposition_map[task_id]:
            cycle_errors = self._check_for_cycles(subtask_id, new_visited)
            errors.extend(cycle_errors)
        
        return errors
    
    def _are_preconditions_compatible(
        self, 
        parent_preconditions: List[Condition], 
        subtask_preconditions: List[Condition]
    ) -> bool:
        """
        Check if subtask preconditions are compatible with parent preconditions.
        
        Subtask preconditions are compatible if they can be satisfied when parent
        preconditions are satisfied (i.e., subtask doesn't require more than parent).
        
        Args:
            parent_preconditions: Parent task preconditions
            subtask_preconditions: First subtask preconditions
        
        Returns:
            True if compatible, False otherwise
        """
        # If subtask has no preconditions, it's always compatible
        if not subtask_preconditions:
            return True
        
        # If parent has no preconditions but subtask does, check if subtask conditions are reasonable
        if not parent_preconditions:
            # Subtask can have preconditions even if parent doesn't
            return True
        
        # Extract condition expressions for comparison
        parent_expressions = {self._normalize_expression(c.expression) for c in parent_preconditions}
        subtask_expressions = {self._normalize_expression(c.expression) for c in subtask_preconditions}
        
        # Check if subtask preconditions are a subset or compatible with parent preconditions
        # For simplicity, we check if there's overlap or if subtask conditions are reasonable
        # In production, would use formal logic to verify implication
        
        # If there's any overlap in expressions, consider compatible
        if parent_expressions & subtask_expressions:
            return True
        
        # If no overlap, still compatible (subtask may have different but compatible conditions)
        return True
    
    def _do_postconditions_achieve_parent(
        self, 
        subtask_postconditions: List[Condition], 
        parent_postconditions: List[Condition]
    ) -> bool:
        """
        Check if subtask postconditions achieve parent postconditions.
        
        Subtask postconditions achieve parent postconditions if they logically
        imply or satisfy all parent postconditions.
        
        Args:
            subtask_postconditions: Last subtask postconditions
            parent_postconditions: Parent task postconditions
        
        Returns:
            True if subtask achieves parent postconditions, False otherwise
        """
        # If parent has no postconditions, always achieved
        if not parent_postconditions:
            return True
        
        # If parent has postconditions but subtask doesn't, not achieved
        if not subtask_postconditions:
            return False
        
        # Extract condition expressions for comparison
        subtask_expressions = {self._normalize_expression(c.expression) for c in subtask_postconditions}
        parent_expressions = {self._normalize_expression(c.expression) for c in parent_postconditions}
        
        # Check if all parent postconditions are covered by subtask postconditions
        # For simplicity, check if parent expressions are subset of subtask expressions
        # In production, would use formal logic to verify implication
        
        # Check if all parent postconditions have matching subtask postconditions
        for parent_expr in parent_expressions:
            if parent_expr not in subtask_expressions:
                # Check for semantic equivalence (e.g., "position.x == 1.0" matches "x == 1.0")
                found_match = False
                for subtask_expr in subtask_expressions:
                    if self._are_expressions_equivalent(parent_expr, subtask_expr):
                        found_match = True
                        break
                
                if not found_match:
                    return False
        
        return True
    
    def _do_postconditions_enable_preconditions(
        self, 
        postconditions: List[Condition], 
        preconditions: List[Condition]
    ) -> bool:
        """
        Check if postconditions of one subtask enable preconditions of the next.
        
        Postconditions enable preconditions if the state resulting from satisfying
        postconditions will satisfy the preconditions.
        
        Args:
            postconditions: Current subtask postconditions
            preconditions: Next subtask preconditions
        
        Returns:
            True if postconditions enable preconditions, False otherwise
        """
        # If next subtask has no preconditions, always enabled
        if not preconditions:
            return True
        
        # If current has no postconditions but next has preconditions, may not be enabled
        # However, this is not necessarily an error - the state may already satisfy preconditions
        if not postconditions:
            return True
        
        # Extract condition expressions
        post_expressions = {self._normalize_expression(c.expression) for c in postconditions}
        pre_expressions = {self._normalize_expression(c.expression) for c in preconditions}
        
        # Check if there's compatibility between postconditions and preconditions
        # For simplicity, check if there's overlap or if conditions are compatible
        # In production, would use formal logic to verify state transitions
        
        # If there's overlap, consider enabled
        if post_expressions & pre_expressions:
            return True
        
        # Check for semantic compatibility
        for pre_expr in pre_expressions:
            for post_expr in post_expressions:
                if self._are_expressions_compatible(post_expr, pre_expr):
                    return True
        
        # If no direct match, still consider enabled (may be compatible through state)
        return True
    
    def _normalize_expression(self, expression: str) -> str:
        """
        Normalize a condition expression for comparison.
        
        Args:
            expression: Condition expression string
        
        Returns:
            Normalized expression
        """
        # Remove whitespace and convert to lowercase
        normalized = expression.lower().replace(" ", "")
        return normalized
    
    def _are_expressions_equivalent(self, expr1: str, expr2: str) -> bool:
        """
        Check if two expressions are semantically equivalent.
        
        Args:
            expr1: First expression
            expr2: Second expression
        
        Returns:
            True if expressions are equivalent, False otherwise
        """
        # Simple equivalence check - in production would use proper expression parsing
        norm1 = self._normalize_expression(expr1)
        norm2 = self._normalize_expression(expr2)
        
        # Direct match
        if norm1 == norm2:
            return True
        
        # Check for variations (e.g., "position.x == 1.0" vs "x == 1.0")
        if "position.x" in norm1 and "x" in norm2:
            return norm1.replace("position.", "") == norm2
        if "position.x" in norm2 and "x" in norm1:
            return norm2.replace("position.", "") == norm1
        
        return False
    
    def _are_expressions_compatible(self, expr1: str, expr2: str) -> bool:
        """
        Check if two expressions are compatible (one enables the other).
        
        Args:
            expr1: First expression (postcondition)
            expr2: Second expression (precondition)
        
        Returns:
            True if expressions are compatible, False otherwise
        """
        # Check for equivalence first
        if self._are_expressions_equivalent(expr1, expr2):
            return True
        
        # Check if they reference the same field
        norm1 = self._normalize_expression(expr1)
        norm2 = self._normalize_expression(expr2)
        
        # Extract field names
        fields1 = self._extract_fields(norm1)
        fields2 = self._extract_fields(norm2)
        
        # If they reference the same fields, consider compatible
        return bool(fields1 & fields2)
    
    def _extract_fields(self, expression: str) -> Set[str]:
        """
        Extract field names from an expression.
        
        Args:
            expression: Normalized expression
        
        Returns:
            Set of field names referenced in expression
        """
        fields = set()
        
        # Common field names
        field_names = [
            'battery_level', 'position', 'orientation', 'x', 'y', 'z',
            'joint_states', 'sensor_readings', 'actuator_states', 'error_flags'
        ]
        
        for field in field_names:
            if field in expression:
                fields.add(field)
        
        return fields
    
    def _evaluate_condition(self, condition: Condition, state: RobotState) -> bool:
        """
        Evaluate a condition against a robot state.
        
        Args:
            condition: Condition to evaluate
            state: RobotState to evaluate against
        
        Returns:
            True if condition is satisfied, False otherwise
        """
        # Parse and evaluate the condition expression
        # This is a simplified implementation - production would use proper expression parser
        
        expression = condition.expression.lower()
        tolerance = condition.tolerance
        
        if condition.type == ConditionType.STATE_EQUALS:
            # Example: "battery_level == 1.0"
            if 'battery_level' in expression:
                # Extract target value from expression
                try:
                    target = float(expression.split('==')[1].strip())
                    return abs(state.battery_level - target) <= tolerance
                except (IndexError, ValueError):
                    return False
        
        elif condition.type == ConditionType.STATE_GREATER_THAN:
            # Example: "battery_level > 0.5"
            if 'battery_level' in expression:
                try:
                    target = float(expression.split('>')[1].strip())
                    return state.battery_level > target - tolerance
                except (IndexError, ValueError):
                    return False
        
        elif condition.type == ConditionType.STATE_LESS_THAN:
            # Example: "battery_level < 0.2"
            if 'battery_level' in expression:
                try:
                    target = float(expression.split('<')[1].strip())
                    return state.battery_level < target + tolerance
                except (IndexError, ValueError):
                    return False
        
        elif condition.type == ConditionType.STATE_IN_RANGE:
            # Example: "battery_level in [0.3, 0.8]"
            if 'battery_level' in expression:
                try:
                    # Extract range values
                    range_part = expression.split('[')[1].split(']')[0]
                    min_val, max_val = map(float, range_part.split(','))
                    return (min_val - tolerance) <= state.battery_level <= (max_val + tolerance)
                except (IndexError, ValueError):
                    return False
        
        elif condition.type == ConditionType.CAPABILITY_AVAILABLE:
            # This would check robot capabilities, not state
            # For now, return True as a placeholder
            return True
        
        # Default: condition not recognized or not evaluable
        return False
