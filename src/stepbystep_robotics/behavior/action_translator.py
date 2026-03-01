"""
Action Translator component for StepbyStep:ROBOTICS.

This module provides bidirectional translation between low-level robot actions
and human-readable descriptions. It's the core of the Behavior Layer - the compiler
that converts between human understanding and robot execution.

Key capabilities:
- translateToHuman(): Convert robot actions to human-readable descriptions
- translateToRobot(): Parse human commands into executable robot actions
- explainBehavior(): Generate narrative explanations of robot behavior sequences
- validateTranslation(): Verify bidirectional translation accuracy
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from ..models import RobotState, ActionType
from .state_observer import StateHistory


@dataclass
class RobotAction:
    """
    Low-level robot action with parameters.
    
    This represents the actual commands sent to the robot controller,
    including motion primitives, sensor queries, and actuator commands.
    """
    action_id: str
    action_type: ActionType
    parameters: Dict[str, Any]
    timestamp: datetime
    robot_id: UUID
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate robot action."""
        if not self.action_id:
            raise ValueError("action_id cannot be empty")
        if not isinstance(self.action_type, ActionType):
            raise ValueError("action_type must be an ActionType")
        if not isinstance(self.parameters, dict):
            raise ValueError("parameters must be a dictionary")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime")
        if not isinstance(self.robot_id, UUID):
            raise ValueError("robot_id must be a valid UUID")


@dataclass
class HumanReadableDescription:
    """
    Human-readable description of a robot action.
    
    This is what operators see - natural language descriptions that explain
    what the robot is doing in terms humans can understand.
    """
    description: str
    confidence: float
    action_type: ActionType
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    original_action: Optional[RobotAction] = None
    
    def __post_init__(self):
        """Validate human readable description."""
        if not self.description:
            raise ValueError("description cannot be empty")
        if not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be numeric")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not isinstance(self.action_type, ActionType):
            raise ValueError("action_type must be an ActionType")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime")
    
    def is_low_confidence(self) -> bool:
        """Check if this translation has low confidence (<95%)."""
        return self.confidence < 0.95


@dataclass
class HumanCommand:
    """
    Natural language command from a human operator.
    
    This is what operators input - their intent expressed in natural language
    that needs to be parsed into executable robot actions.
    """
    command_text: str
    operator_id: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate human command."""
        if not self.command_text:
            raise ValueError("command_text cannot be empty")
        if not self.operator_id:
            raise ValueError("operator_id cannot be empty")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime")


@dataclass
class RobotActionSequence:
    """
    Sequence of robot actions to execute a human command.
    
    A single human command often translates to multiple robot actions
    that need to be executed in sequence.
    """
    actions: List[RobotAction]
    confidence: float
    original_command: HumanCommand
    estimated_duration: float
    
    def __post_init__(self):
        """Validate robot action sequence."""
        if not isinstance(self.actions, list):
            raise ValueError("actions must be a list")
        if len(self.actions) == 0:
            raise ValueError("actions cannot be empty")
        if not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be numeric")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not isinstance(self.original_command, HumanCommand):
            raise ValueError("original_command must be a HumanCommand")
        if not isinstance(self.estimated_duration, (int, float)):
            raise ValueError("estimated_duration must be numeric")
        if self.estimated_duration < 0:
            raise ValueError("estimated_duration must be non-negative")


@dataclass
class BehaviorNarrative:
    """
    Human-readable narrative explaining robot behavior over time.
    
    This is the "story" of what the robot did - a sequence of descriptions
    that explain the robot's behavior in a way humans can understand.
    """
    narrative_segments: List[str]
    confidence: float
    state_history: StateHistory
    duration: float
    summary: str
    
    def __post_init__(self):
        """Validate behavior narrative."""
        if not isinstance(self.narrative_segments, list):
            raise ValueError("narrative_segments must be a list")
        if len(self.narrative_segments) == 0:
            raise ValueError("narrative_segments cannot be empty")
        if not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be numeric")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not isinstance(self.state_history, StateHistory):
            raise ValueError("state_history must be a StateHistory")
        if not isinstance(self.duration, (int, float)):
            raise ValueError("duration must be numeric")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")
        if not self.summary:
            raise ValueError("summary cannot be empty")


@dataclass
class ValidationResult:
    """
    Result of translation validation.
    
    Measures how accurately a translation preserves semantic meaning
    and goal equivalence in bidirectional translation.
    """
    is_valid: bool
    accuracy: float
    semantic_equivalence: bool
    goal_equivalence: bool
    differences: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate validation result."""
        if not isinstance(self.is_valid, bool):
            raise ValueError("is_valid must be a boolean")
        if not isinstance(self.accuracy, (int, float)):
            raise ValueError("accuracy must be numeric")
        if not 0.0 <= self.accuracy <= 1.0:
            raise ValueError("accuracy must be between 0.0 and 1.0")
        if not isinstance(self.semantic_equivalence, bool):
            raise ValueError("semantic_equivalence must be a boolean")
        if not isinstance(self.goal_equivalence, bool):
            raise ValueError("goal_equivalence must be a boolean")
        if not isinstance(self.differences, list):
            raise ValueError("differences must be a list")


class ActionTranslator:
    """
    Converts between low-level robot actions and human-readable descriptions.
    
    This is the core of the Behavior Layer - the compiler that makes robots legible.
    It translates robot motion patterns into human understanding with smoothness,
    tempo, and transition parameters.
    
    Key responsibilities:
    - Map low-level motor commands to high-level action descriptions
    - Parse natural language commands into executable robot instructions
    - Generate contextual explanations of robot behavior sequences
    - Ensure bidirectional translation accuracy and consistency
    """
    
    def __init__(self):
        """Initialize the action translator."""
        # Translation mappings for common actions
        self._action_templates = self._initialize_action_templates()
        
        # Confidence thresholds
        self.low_confidence_threshold = 0.95
        self.minimum_confidence = 0.5
    
    def _initialize_action_templates(self) -> Dict[ActionType, Dict[str, Any]]:
        """
        Initialize translation templates for common action types.
        
        These templates define how to translate between robot actions
        and human descriptions for standard action types.
        """
        return {
            ActionType.MOVE: {
                "template": "Moving to position ({x:.2f}, {y:.2f}, {z:.2f})",
                "keywords": ["move", "go", "navigate", "travel"],
                "parameters": ["target_position", "speed", "trajectory"],
            },
            ActionType.GRASP: {
                "template": "Grasping object with {force:.1f}N force",
                "keywords": ["grasp", "grab", "pick", "hold"],
                "parameters": ["target_object", "force", "grip_type"],
            },
            ActionType.RELEASE: {
                "template": "Releasing object",
                "keywords": ["release", "drop", "let go", "place"],
                "parameters": ["target_location", "release_speed"],
            },
            ActionType.ROTATE: {
                "template": "Rotating {angle:.1f} degrees around {axis}",
                "keywords": ["rotate", "turn", "spin", "orient"],
                "parameters": ["angle", "axis", "speed"],
            },
            ActionType.WAIT: {
                "template": "Waiting for {duration:.1f} seconds",
                "keywords": ["wait", "pause", "hold", "delay"],
                "parameters": ["duration", "condition"],
            },
            ActionType.SENSE: {
                "template": "Sensing {sensor_type}",
                "keywords": ["sense", "measure", "detect", "scan"],
                "parameters": ["sensor_type", "target"],
            },
        }
    
    def translateToHuman(self, action: RobotAction) -> HumanReadableDescription:
        """
        Translate a robot action to human-readable description.
        
        This is where "yoga compiles movement" - translating robot motion patterns
        into human understanding with smoothness, tempo, and transition parameters.
        
        For low-confidence translations (<95%), the original action data is attached
        for operator reference and verification.
        
        Args:
            action: The robot action to translate
            
        Returns:
            Human-readable description with confidence score
            
        Requirements: 2.1, 2.2, 2.5, 2.4, 12.1, 12.2, 12.3
        """
        if not isinstance(action, RobotAction):
            raise ValueError("action must be a RobotAction")
        
        # Get template for this action type
        template_info = self._action_templates.get(action.action_type)
        
        if template_info is None:
            # Unknown action type - low confidence translation
            description = f"Performing {action.action_type.value} action"
            confidence = 0.6
        else:
            # Use template to generate description
            try:
                description = self._apply_template(template_info["template"], action.parameters)
                confidence = self._calculate_confidence(action, template_info)
            except Exception:
                # Template application failed - fallback to generic description
                description = f"Performing {action.action_type.value} action"
                confidence = 0.7
        
        # Build context with robot information
        context = {
            "robot_id": str(action.robot_id),
            "action_id": action.action_id,
        }
        
        # For low-confidence translations, add additional context
        is_low_confidence = confidence < self.low_confidence_threshold
        if is_low_confidence:
            context["low_confidence"] = True
            context["confidence_score"] = confidence
            context["reason"] = self._get_low_confidence_reason(action, template_info, confidence)
        
        return HumanReadableDescription(
            description=description,
            confidence=confidence,
            action_type=action.action_type,
            timestamp=action.timestamp,
            context=context,
            original_action=action if is_low_confidence else None,
        )
    
    def _get_low_confidence_reason(
        self, 
        action: RobotAction, 
        template_info: Optional[Dict[str, Any]], 
        confidence: float
    ) -> str:
        """
        Generate explanation for why translation has low confidence.
        
        This helps operators understand what caused the uncertainty.
        
        Args:
            action: The robot action being translated
            template_info: Template information (if available)
            confidence: Calculated confidence score
            
        Returns:
            Human-readable explanation of low confidence
            
        Requirements: 12.2, 12.3
        """
        reasons = []
        
        if template_info is None:
            reasons.append("Unknown action type")
        else:
            # Check for missing parameters
            expected_params = template_info.get("parameters", [])
            missing_params = [p for p in expected_params if p not in action.parameters]
            if missing_params:
                reasons.append(f"Missing parameters: {', '.join(missing_params)}")
            
            # Check for invalid parameters
            for param in expected_params:
                if param in action.parameters:
                    value = action.parameters[param]
                    if value is None or (isinstance(value, (str, dict, list)) and not value):
                        reasons.append(f"Invalid parameter value: {param}")
        
        # Check metadata
        if not action.metadata or len(action.metadata) == 0:
            reasons.append("Insufficient metadata")
        
        if not reasons:
            reasons.append(f"Confidence score {confidence:.2%} below threshold")
        
        return "; ".join(reasons)

    
    def translateToRobot(self, command: HumanCommand) -> RobotActionSequence:
        """
        Parse a human command into executable robot action sequence.
        
        Converts natural language intent into precise robot motion primitives
        that can be executed by the robot controller.
        
        Args:
            command: The human command to parse
            
        Returns:
            Sequence of robot actions to execute the command
            
        Requirements: 2.1, 2.2, 2.5
        """
        if not isinstance(command, HumanCommand):
            raise ValueError("command must be a HumanCommand")
        
        # Parse command text to identify action type and parameters
        command_lower = command.command_text.lower()
        
        # Find matching action type based on keywords
        matched_action_type = None
        matched_confidence = 0.0
        
        for action_type, template_info in self._action_templates.items():
            for keyword in template_info["keywords"]:
                if keyword in command_lower:
                    matched_action_type = action_type
                    matched_confidence = 0.85  # Base confidence for keyword match
                    break
            if matched_action_type:
                break
        
        if matched_action_type is None:
            # No clear match - default to CUSTOM action with low confidence
            matched_action_type = ActionType.CUSTOM
            matched_confidence = 0.6
        
        # Extract parameters from command (simplified for now)
        parameters = self._extract_parameters(command.command_text, matched_action_type)
        
        # Create robot action
        robot_action = RobotAction(
            action_id=f"action_{command.timestamp.timestamp()}",
            action_type=matched_action_type,
            parameters=parameters,
            timestamp=command.timestamp,
            robot_id=UUID(command.context.get("robot_id", "00000000-0000-0000-0000-000000000000")),
            metadata={"operator_id": command.operator_id},
        )
        
        # Estimate duration based on action type
        estimated_duration = self._estimate_duration(matched_action_type, parameters)
        
        return RobotActionSequence(
            actions=[robot_action],
            confidence=matched_confidence,
            original_command=command,
            estimated_duration=estimated_duration,
        )
    
    def explainBehavior(self, state_sequence: StateHistory) -> BehaviorNarrative:
        """
        Generate narrative explanation of robot behavior from state sequence.
        
        Analyzes how the robot's state changed over time and creates a
        human-readable story of what the robot did.
        
        Args:
            state_sequence: Sequence of robot states to explain
            
        Returns:
            Narrative explanation of the behavior
            
        Requirements: 2.1, 2.2, 2.5
        """
        if not isinstance(state_sequence, StateHistory):
            raise ValueError("state_sequence must be a StateHistory")
        
        if len(state_sequence.states) < 2:
            raise ValueError("state_sequence must contain at least 2 states")
        
        narrative_segments = []
        total_confidence = 0.0
        
        # Analyze state transitions
        for i in range(len(state_sequence.states) - 1):
            current_state = state_sequence.states[i]
            next_state = state_sequence.states[i + 1]
            
            # Detect significant changes
            segment, confidence = self._analyze_state_transition(current_state, next_state)
            
            if segment:
                narrative_segments.append(segment)
                total_confidence += confidence
        
        # Calculate average confidence
        avg_confidence = total_confidence / len(narrative_segments) if narrative_segments else 0.5
        
        # Generate summary
        start_time = state_sequence.states[0].timestamp
        end_time = state_sequence.states[-1].timestamp
        duration = (end_time - start_time).total_seconds()
        summary = self._generate_summary(narrative_segments, duration)
        
        return BehaviorNarrative(
            narrative_segments=narrative_segments if narrative_segments else ["Robot maintained position"],
            confidence=avg_confidence,
            state_history=state_sequence,
            duration=duration,
            summary=summary,
        )
    
    def validateTranslation(
        self, 
        original: RobotAction, 
        translated: HumanReadableDescription
    ) -> ValidationResult:
        """
        Validate bidirectional translation accuracy.
        
        Ensures that translating to human and back to robot preserves
        semantic meaning and goal equivalence.
        
        Args:
            original: Original robot action
            translated: Human-readable translation
            
        Returns:
            Validation result with accuracy metrics
            
        Requirements: 2.3, 2.5
        """
        if not isinstance(original, RobotAction):
            raise ValueError("original must be a RobotAction")
        if not isinstance(translated, HumanReadableDescription):
            raise ValueError("translated must be a HumanReadableDescription")
        
        differences = []
        
        # Check action type match
        action_type_match = original.action_type == translated.action_type
        if not action_type_match:
            differences.append(
                f"Action type mismatch: {original.action_type.value} vs {translated.action_type.value}"
            )
        
        # Check timestamp consistency
        time_diff = abs((original.timestamp - translated.timestamp).total_seconds())
        if time_diff > 1.0:  # Allow 1 second tolerance
            differences.append(f"Timestamp difference: {time_diff:.2f} seconds")
        
        # Calculate accuracy based on confidence and matches
        accuracy = translated.confidence
        if not action_type_match:
            accuracy *= 0.5  # Significant penalty for action type mismatch
        
        # Semantic equivalence: Do they represent the same action?
        semantic_equivalence = action_type_match and accuracy >= 0.8
        
        # Goal equivalence: Would they achieve the same result?
        goal_equivalence = action_type_match and accuracy >= 0.9
        
        is_valid = accuracy >= self.minimum_confidence and action_type_match
        
        return ValidationResult(
            is_valid=is_valid,
            accuracy=accuracy,
            semantic_equivalence=semantic_equivalence,
            goal_equivalence=goal_equivalence,
            differences=differences,
        )
    
    # Helper methods
    
    def _apply_template(self, template: str, parameters: Dict[str, Any]) -> str:
        """Apply template with parameters to generate description."""
        try:
            # Handle nested parameters (e.g., target_position.x)
            flat_params = {}
            for key, value in parameters.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        flat_params[subkey] = subvalue
                else:
                    flat_params[key] = value
            
            return template.format(**flat_params)
        except (KeyError, ValueError):
            # Template formatting failed - return generic description
            return f"Performing action with parameters: {parameters}"
    
    def _calculate_confidence(self, action: RobotAction, template_info: Dict[str, Any]) -> float:
        """
        Calculate confidence score for translation.
        
        Confidence is based on multiple factors:
        - Parameter completeness: Are all expected parameters present?
        - Parameter validity: Are parameter values within expected ranges?
        - Action type familiarity: Is this a well-known action type?
        - Metadata quality: Is there sufficient context information?
        
        Returns:
            Confidence score between 0.0 and 1.0
            
        Requirements: 2.4, 12.1
        """
        confidence = 0.98  # Start with high baseline confidence
        
        # Factor 1: Check if all expected parameters are present
        expected_params = template_info.get("parameters", [])
        missing_params = [p for p in expected_params if p not in action.parameters]
        
        if missing_params:
            # Reduce confidence for each missing parameter
            # Missing critical parameters significantly reduce confidence
            confidence -= 0.08 * len(missing_params)
        
        # Factor 2: Check parameter validity and completeness
        present_params = [p for p in expected_params if p in action.parameters]
        if present_params:
            # Check if parameter values are valid (not None, not empty)
            invalid_params = 0
            for param in present_params:
                value = action.parameters[param]
                if value is None or (isinstance(value, (str, dict, list)) and not value):
                    invalid_params += 1
            
            if invalid_params > 0:
                confidence -= 0.05 * invalid_params
        
        # Factor 3: Check for unexpected parameters (might indicate confusion)
        unexpected_params = [p for p in action.parameters if p not in expected_params]
        if unexpected_params:
            # Slight reduction for unexpected parameters
            confidence -= 0.02 * len(unexpected_params)
        
        # Factor 4: Check metadata quality
        if not action.metadata or len(action.metadata) == 0:
            # Lack of metadata slightly reduces confidence
            confidence -= 0.02
        
        # Factor 5: Validate parameter types for known parameters
        if action.action_type == ActionType.MOVE:
            # Check if target_position has proper structure
            if "target_position" in action.parameters:
                pos = action.parameters["target_position"]
                if not isinstance(pos, dict) or not all(k in pos for k in ["x", "y", "z"]):
                    confidence -= 0.05
        
        elif action.action_type == ActionType.GRASP:
            # Check if force is a reasonable value
            if "force" in action.parameters:
                force = action.parameters["force"]
                if not isinstance(force, (int, float)) or force < 0 or force > 1000:
                    confidence -= 0.05
        
        elif action.action_type == ActionType.ROTATE:
            # Check if angle is reasonable
            if "angle" in action.parameters:
                angle = action.parameters["angle"]
                if not isinstance(angle, (int, float)) or abs(angle) > 360:
                    confidence -= 0.03
        
        # Ensure confidence is in valid range
        return max(self.minimum_confidence, min(1.0, confidence))
    
    def _extract_parameters(self, command_text: str, action_type: ActionType) -> Dict[str, Any]:
        """Extract parameters from command text (simplified implementation)."""
        # This is a simplified implementation
        # A real implementation would use NLP to extract parameters
        parameters = {}
        
        # Extract numeric values
        import re
        numbers = re.findall(r'-?\d+\.?\d*', command_text)
        
        if action_type == ActionType.MOVE and len(numbers) >= 3:
            parameters["target_position"] = {
                "x": float(numbers[0]),
                "y": float(numbers[1]),
                "z": float(numbers[2]),
            }
        elif action_type == ActionType.ROTATE and len(numbers) >= 1:
            parameters["angle"] = float(numbers[0])
            parameters["axis"] = "z"  # Default axis
        elif action_type == ActionType.WAIT and len(numbers) >= 1:
            parameters["duration"] = float(numbers[0])
        elif action_type == ActionType.GRASP and len(numbers) >= 1:
            parameters["force"] = float(numbers[0])
        
        return parameters
    
    def _estimate_duration(self, action_type: ActionType, parameters: Dict[str, Any]) -> float:
        """Estimate execution duration for action."""
        # Simplified duration estimation
        duration_map = {
            ActionType.MOVE: 5.0,
            ActionType.GRASP: 2.0,
            ActionType.RELEASE: 1.0,
            ActionType.ROTATE: 3.0,
            ActionType.WAIT: parameters.get("duration", 1.0),
            ActionType.SENSE: 0.5,
            ActionType.CUSTOM: 5.0,
        }
        return duration_map.get(action_type, 5.0)
    
    def _analyze_state_transition(
        self, 
        current: RobotState, 
        next_state: RobotState
    ) -> tuple[Optional[str], float]:
        """Analyze transition between two states and generate description."""
        # Calculate position change
        pos_change = (
            (next_state.position.x - current.position.x) ** 2 +
            (next_state.position.y - current.position.y) ** 2 +
            (next_state.position.z - current.position.z) ** 2
        ) ** 0.5
        
        # Significant position change
        if pos_change > 0.1:  # 10cm threshold
            segment = f"Moved {pos_change:.2f}m to position ({next_state.position.x:.2f}, {next_state.position.y:.2f}, {next_state.position.z:.2f})"
            return segment, 0.9
        
        # Check battery level change
        battery_change = abs(next_state.battery_level - current.battery_level)
        if battery_change > 0.05:  # 5% threshold
            if next_state.battery_level < current.battery_level:
                segment = f"Battery decreased to {next_state.battery_level * 100:.1f}%"
            else:
                segment = f"Battery increased to {next_state.battery_level * 100:.1f}%"
            return segment, 0.85
        
        # Check for new error flags
        new_errors = next_state.error_flags - current.error_flags
        if new_errors:
            segment = f"Encountered errors: {', '.join(new_errors)}"
            return segment, 0.95
        
        # No significant change detected
        return None, 0.5
    
    def _generate_summary(self, segments: List[str], duration: float) -> str:
        """Generate summary of behavior narrative."""
        if not segments:
            return f"Robot maintained position for {duration:.1f} seconds"
        
        action_count = len(segments)
        return f"Robot performed {action_count} action(s) over {duration:.1f} seconds"
