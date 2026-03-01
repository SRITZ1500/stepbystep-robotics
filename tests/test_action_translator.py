"""
Unit tests for ActionTranslator component.

Tests verify:
- Robot action to human translation
- Human command to robot action translation
- Behavior narrative generation from state sequences
- Bidirectional translation validation
- Confidence scoring and low-confidence flagging
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.stepbystep_robotics.models import (
    RobotState,
    Vector3D,
    Quaternion,
    JointState,
    ActionType,
)
from src.stepbystep_robotics.behavior import (
    ActionTranslator,
    RobotAction,
    HumanReadableDescription,
    HumanCommand,
    RobotActionSequence,
    BehaviorNarrative,
    ValidationResult,
    StateHistory,
)


def create_test_robot_state(robot_id, timestamp, position=None, battery_level=0.8):
    """Helper to create a test robot state."""
    if position is None:
        position = Vector3D(1.0, 2.0, 3.0)
    
    return RobotState(
        robot_id=robot_id,
        timestamp=timestamp,
        position=position,
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={
            "joint1": JointState("joint1", 0.5, 0.1, 0.2, 25.0)
        },
        sensor_readings={"sensor1": 42.0},
        actuator_states={"actuator1": "active"},
        battery_level=battery_level,
        error_flags=set(),
    )


class TestActionTranslator:
    """Test suite for ActionTranslator component."""
    
    def test_translator_initialization(self):
        """Test that ActionTranslator initializes correctly."""
        translator = ActionTranslator()
        
        assert translator is not None
        assert translator.low_confidence_threshold == 0.95
        assert translator.minimum_confidence == 0.5
        assert len(translator._action_templates) > 0
    
    def test_translate_to_human_move_action(self):
        """Test translating a MOVE action to human description."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="move_001",
            action_type=ActionType.MOVE,
            parameters={
                "target_position": {"x": 5.0, "y": 3.0, "z": 2.0},
                "speed": 1.0,
            },
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        assert isinstance(description, HumanReadableDescription)
        assert "Moving to position" in description.description
        assert "5.00" in description.description
        assert "3.00" in description.description
        assert "2.00" in description.description
        assert description.action_type == ActionType.MOVE
        assert description.confidence >= 0.5
        assert description.timestamp == timestamp
    
    def test_translate_to_human_grasp_action(self):
        """Test translating a GRASP action to human description."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="grasp_001",
            action_type=ActionType.GRASP,
            parameters={
                "target_object": "box",
                "force": 10.5,
            },
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        assert isinstance(description, HumanReadableDescription)
        assert "Grasping" in description.description
        assert "10.5" in description.description
        assert description.action_type == ActionType.GRASP
        assert description.confidence >= 0.5
    
    def test_translate_to_human_unknown_action(self):
        """Test translating an unknown action type has lower confidence."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="custom_001",
            action_type=ActionType.CUSTOM,
            parameters={},
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        assert isinstance(description, HumanReadableDescription)
        assert description.action_type == ActionType.CUSTOM
        # Unknown actions should have lower confidence
        assert description.confidence < 0.95
    
    def test_translate_to_human_low_confidence_attaches_original(self):
        """Test that low confidence translations attach original action."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="custom_001",
            action_type=ActionType.CUSTOM,
            parameters={},
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        if description.confidence < 0.95:
            assert description.original_action is not None
            assert description.original_action == action
    
    def test_translate_to_robot_move_command(self):
        """Test translating a human move command to robot action."""
        translator = ActionTranslator()
        timestamp = datetime.now()
        robot_id = uuid4()
        
        command = HumanCommand(
            command_text="move to 5.0 3.0 2.0",
            operator_id="operator_001",
            timestamp=timestamp,
            context={"robot_id": str(robot_id)},
        )
        
        sequence = translator.translateToRobot(command)
        
        assert isinstance(sequence, RobotActionSequence)
        assert len(sequence.actions) > 0
        assert sequence.actions[0].action_type == ActionType.MOVE
        assert sequence.confidence >= 0.5
        assert sequence.original_command == command
        assert sequence.estimated_duration > 0
    
    def test_translate_to_robot_grasp_command(self):
        """Test translating a human grasp command to robot action."""
        translator = ActionTranslator()
        timestamp = datetime.now()
        robot_id = uuid4()
        
        command = HumanCommand(
            command_text="grasp the object with 10 N force",
            operator_id="operator_001",
            timestamp=timestamp,
            context={"robot_id": str(robot_id)},
        )
        
        sequence = translator.translateToRobot(command)
        
        assert isinstance(sequence, RobotActionSequence)
        assert len(sequence.actions) > 0
        assert sequence.actions[0].action_type == ActionType.GRASP
        assert sequence.confidence >= 0.5
    
    def test_translate_to_robot_unknown_command(self):
        """Test translating an unknown command defaults to CUSTOM action."""
        translator = ActionTranslator()
        timestamp = datetime.now()
        robot_id = uuid4()
        
        command = HumanCommand(
            command_text="do something weird",
            operator_id="operator_001",
            timestamp=timestamp,
            context={"robot_id": str(robot_id)},
        )
        
        sequence = translator.translateToRobot(command)
        
        assert isinstance(sequence, RobotActionSequence)
        assert len(sequence.actions) > 0
        # Unknown commands should have lower confidence
        assert sequence.confidence < 0.95
    
    def test_explain_behavior_with_position_change(self):
        """Test generating behavior narrative from state sequence with position change."""
        translator = ActionTranslator()
        robot_id = uuid4()
        start_time = datetime.now()
        
        # Create state sequence with position change
        states = [
            create_test_robot_state(
                robot_id, 
                start_time, 
                position=Vector3D(0.0, 0.0, 0.0)
            ),
            create_test_robot_state(
                robot_id, 
                start_time + timedelta(seconds=1), 
                position=Vector3D(1.0, 0.0, 0.0)
            ),
            create_test_robot_state(
                robot_id, 
                start_time + timedelta(seconds=2), 
                position=Vector3D(2.0, 0.0, 0.0)
            ),
        ]
        
        state_history = StateHistory(robot_id, states)
        narrative = translator.explainBehavior(state_history)
        
        assert isinstance(narrative, BehaviorNarrative)
        assert len(narrative.narrative_segments) > 0
        assert narrative.confidence >= 0.5
        assert narrative.duration >= 0
        assert narrative.summary
        assert "Moved" in narrative.narrative_segments[0]
    
    def test_explain_behavior_with_battery_change(self):
        """Test generating behavior narrative with battery level change."""
        translator = ActionTranslator()
        robot_id = uuid4()
        start_time = datetime.now()
        
        # Create state sequence with battery change
        states = [
            create_test_robot_state(robot_id, start_time, battery_level=0.9),
            create_test_robot_state(robot_id, start_time + timedelta(seconds=1), battery_level=0.8),
        ]
        
        state_history = StateHistory(robot_id, states)
        narrative = translator.explainBehavior(state_history)
        
        assert isinstance(narrative, BehaviorNarrative)
        assert len(narrative.narrative_segments) > 0
        assert "Battery" in narrative.narrative_segments[0]
    
    def test_explain_behavior_requires_at_least_two_states(self):
        """Test that explainBehavior requires at least 2 states."""
        translator = ActionTranslator()
        robot_id = uuid4()
        start_time = datetime.now()
        
        states = [create_test_robot_state(robot_id, start_time)]
        state_history = StateHistory(robot_id, states)
        
        with pytest.raises(ValueError, match="at least 2 states"):
            translator.explainBehavior(state_history)
    
    def test_validate_translation_matching_action_types(self):
        """Test validation with matching action types."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        original = RobotAction(
            action_id="move_001",
            action_type=ActionType.MOVE,
            parameters={"target_position": {"x": 5.0, "y": 3.0, "z": 2.0}},
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        translated = HumanReadableDescription(
            description="Moving to position (5.00, 3.00, 2.00)",
            confidence=0.95,
            action_type=ActionType.MOVE,
            timestamp=timestamp,
        )
        
        result = translator.validateTranslation(original, translated)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert result.accuracy >= 0.5
        assert result.semantic_equivalence
        assert result.goal_equivalence
    
    def test_validate_translation_mismatched_action_types(self):
        """Test validation with mismatched action types."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        original = RobotAction(
            action_id="move_001",
            action_type=ActionType.MOVE,
            parameters={},
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        translated = HumanReadableDescription(
            description="Grasping object",
            confidence=0.95,
            action_type=ActionType.GRASP,
            timestamp=timestamp,
        )
        
        result = translator.validateTranslation(original, translated)
        
        assert isinstance(result, ValidationResult)
        assert not result.is_valid
        assert len(result.differences) > 0
        assert "Action type mismatch" in result.differences[0]
    
    def test_validate_translation_low_confidence(self):
        """Test validation with low confidence translation."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        original = RobotAction(
            action_id="custom_001",
            action_type=ActionType.CUSTOM,
            parameters={},
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        translated = HumanReadableDescription(
            description="Performing custom action",
            confidence=0.4,  # Below minimum confidence
            action_type=ActionType.CUSTOM,
            timestamp=timestamp,
        )
        
        result = translator.validateTranslation(original, translated)
        
        assert isinstance(result, ValidationResult)
        assert not result.is_valid  # Below minimum confidence threshold
        assert result.accuracy < 0.5
    
    def test_human_readable_description_is_low_confidence(self):
        """Test is_low_confidence method on HumanReadableDescription."""
        high_conf = HumanReadableDescription(
            description="Test",
            confidence=0.96,
            action_type=ActionType.MOVE,
            timestamp=datetime.now(),
        )
        
        low_conf = HumanReadableDescription(
            description="Test",
            confidence=0.90,
            action_type=ActionType.MOVE,
            timestamp=datetime.now(),
        )
        
        assert not high_conf.is_low_confidence()
        assert low_conf.is_low_confidence()


class TestConfidenceScoring:
    """Test suite for enhanced confidence scoring functionality."""
    
    def test_confidence_with_complete_parameters(self):
        """Test confidence scoring with all expected parameters present."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="move_001",
            action_type=ActionType.MOVE,
            parameters={
                "target_position": {"x": 5.0, "y": 3.0, "z": 2.0},
                "speed": 1.0,
                "trajectory": "linear",
            },
            timestamp=timestamp,
            robot_id=robot_id,
            metadata={"source": "operator"},
        )
        
        description = translator.translateToHuman(action)
        
        # With all parameters and metadata, confidence should be high
        assert description.confidence >= 0.95
        assert description.original_action is None  # High confidence, no need to attach
    
    def test_confidence_with_missing_parameters(self):
        """Test confidence scoring with missing expected parameters."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="move_002",
            action_type=ActionType.MOVE,
            parameters={
                "target_position": {"x": 5.0, "y": 3.0, "z": 2.0},
                # Missing 'speed' and 'trajectory' parameters
            },
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        # Missing parameters should reduce confidence
        assert description.confidence < 0.95
        assert description.original_action is not None  # Low confidence, attach original
        assert description.is_low_confidence()
    
    def test_confidence_with_invalid_parameter_values(self):
        """Test confidence scoring with invalid parameter values."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="grasp_001",
            action_type=ActionType.GRASP,
            parameters={
                "target_object": "",  # Empty string
                "force": None,  # None value
            },
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        # Invalid parameter values should reduce confidence
        assert description.confidence < 0.95
        assert description.original_action is not None
    
    def test_confidence_with_invalid_force_value(self):
        """Test confidence scoring with out-of-range force value."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="grasp_002",
            action_type=ActionType.GRASP,
            parameters={
                "force": 5000.0,  # Unreasonably high force
            },
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        # Out-of-range values should reduce confidence
        assert description.confidence < 0.98
    
    def test_confidence_with_malformed_position(self):
        """Test confidence scoring with malformed position parameter."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="move_003",
            action_type=ActionType.MOVE,
            parameters={
                "target_position": {"x": 5.0, "y": 3.0},  # Missing 'z'
            },
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        # Malformed position should reduce confidence
        assert description.confidence < 0.98
    
    def test_low_confidence_includes_context(self):
        """Test that low-confidence translations include additional context."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="custom_001",
            action_type=ActionType.CUSTOM,
            parameters={},
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        assert description.confidence < 0.95
        assert "low_confidence" in description.context
        assert description.context["low_confidence"] is True
        assert "confidence_score" in description.context
        assert "reason" in description.context
        assert description.context["reason"]  # Should have a reason
    
    def test_low_confidence_reason_for_unknown_action(self):
        """Test low confidence reason for unknown action type."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="custom_001",
            action_type=ActionType.CUSTOM,
            parameters={},
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        assert "Unknown action type" in description.context["reason"]
    
    def test_low_confidence_reason_for_missing_parameters(self):
        """Test low confidence reason for missing parameters."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="move_004",
            action_type=ActionType.MOVE,
            parameters={},  # All parameters missing
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        assert description.confidence < 0.95
        assert "Missing parameters" in description.context["reason"]
    
    def test_confidence_threshold_exactly_95_percent(self):
        """Test behavior at exactly 95% confidence threshold."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        # Create action that should result in exactly 0.95 confidence
        # This is tricky, but we can test the boundary behavior
        action = RobotAction(
            action_id="move_005",
            action_type=ActionType.MOVE,
            parameters={
                "target_position": {"x": 5.0, "y": 3.0, "z": 2.0},
                "speed": 1.0,
            },
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        # At exactly 0.95, should NOT be flagged as low confidence
        if description.confidence >= 0.95:
            assert not description.is_low_confidence()
            assert description.original_action is None
        else:
            assert description.is_low_confidence()
            assert description.original_action is not None
    
    def test_original_action_attached_for_low_confidence(self):
        """Test that original action is attached for low-confidence translations."""
        translator = ActionTranslator()
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="custom_002",
            action_type=ActionType.CUSTOM,
            parameters={"unknown_param": "value"},
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        description = translator.translateToHuman(action)
        
        # Low confidence should attach original action
        assert description.confidence < 0.95
        assert description.original_action is not None
        assert description.original_action == action
        assert description.original_action.action_id == "custom_002"
        assert description.original_action.parameters == {"unknown_param": "value"}


class TestRobotAction:
    """Test suite for RobotAction data model."""
    
    def test_robot_action_creation(self):
        """Test creating a valid RobotAction."""
        robot_id = uuid4()
        timestamp = datetime.now()
        
        action = RobotAction(
            action_id="test_001",
            action_type=ActionType.MOVE,
            parameters={"speed": 1.0},
            timestamp=timestamp,
            robot_id=robot_id,
        )
        
        assert action.action_id == "test_001"
        assert action.action_type == ActionType.MOVE
        assert action.parameters == {"speed": 1.0}
        assert action.timestamp == timestamp
        assert action.robot_id == robot_id
    
    def test_robot_action_validation(self):
        """Test RobotAction validation."""
        robot_id = uuid4()
        timestamp = datetime.now()
        
        # Empty action_id
        with pytest.raises(ValueError, match="action_id cannot be empty"):
            RobotAction(
                action_id="",
                action_type=ActionType.MOVE,
                parameters={},
                timestamp=timestamp,
                robot_id=robot_id,
            )
        
        # Invalid action_type
        with pytest.raises(ValueError, match="action_type must be an ActionType"):
            RobotAction(
                action_id="test",
                action_type="MOVE",  # String instead of ActionType
                parameters={},
                timestamp=timestamp,
                robot_id=robot_id,
            )


class TestHumanCommand:
    """Test suite for HumanCommand data model."""
    
    def test_human_command_creation(self):
        """Test creating a valid HumanCommand."""
        timestamp = datetime.now()
        
        command = HumanCommand(
            command_text="move forward",
            operator_id="op_001",
            timestamp=timestamp,
        )
        
        assert command.command_text == "move forward"
        assert command.operator_id == "op_001"
        assert command.timestamp == timestamp
    
    def test_human_command_validation(self):
        """Test HumanCommand validation."""
        timestamp = datetime.now()
        
        # Empty command_text
        with pytest.raises(ValueError, match="command_text cannot be empty"):
            HumanCommand(
                command_text="",
                operator_id="op_001",
                timestamp=timestamp,
            )
        
        # Empty operator_id
        with pytest.raises(ValueError, match="operator_id cannot be empty"):
            HumanCommand(
                command_text="move",
                operator_id="",
                timestamp=timestamp,
            )
