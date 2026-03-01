"""
Behavior Layer - Real-time state observation and action translation.

This layer provides legibility through:
- State Observer: Captures and normalizes robot state data
- Action Translator: Converts between robot actions and human descriptions
- Visualization Engine: Renders robot state and behavior
"""

from .state_observer import (
    StateObserver,
    StateStream,
    EventStream,
    StateHistory,
    TimeRange,
    EventType,
    StateEvent,
    SensorDataNormalizer,
)

from .action_translator import (
    ActionTranslator,
    RobotAction,
    HumanReadableDescription,
    HumanCommand,
    RobotActionSequence,
    BehaviorNarrative,
    ValidationResult,
)

__all__ = [
    # State Observer
    "StateObserver",
    "StateStream",
    "EventStream",
    "StateHistory",
    "TimeRange",
    "EventType",
    "StateEvent",
    "SensorDataNormalizer",
    # Action Translator
    "ActionTranslator",
    "RobotAction",
    "HumanReadableDescription",
    "HumanCommand",
    "RobotActionSequence",
    "BehaviorNarrative",
    "ValidationResult",
]
