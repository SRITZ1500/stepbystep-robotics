"""
State Observer component for StepbyStep:ROBOTICS.

This module implements the StateObserver component which captures and normalizes
robot state data from multiple sources in real-time.

Responsibilities:
- Monitor robot sensors, actuators, and internal state continuously
- Normalize heterogeneous data formats into unified state representation
- Buffer and stream state data with configurable sampling rates
- Maintain historical state records for analysis and replay
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Deque, Any, Union, Callable
from uuid import UUID
import threading

from ..models import RobotState, Vector3D, Quaternion, JointState


class SensorDataNormalizer:
    """
    Normalizes heterogeneous sensor data formats into unified representation.
    
    Handles various sensor data formats including:
    - Raw numeric values
    - String-encoded values
    - Structured data (lists, dicts)
    - Unit conversions
    - Range normalization
    
    Requirements: 1.2, 1.5
    """
    
    def __init__(self):
        """Initialize the normalizer with default converters."""
        self._converters: Dict[str, Callable[[Any], float]] = {}
        self._unit_converters: Dict[str, Callable[[float], float]] = {}
        
        # Register default unit converters
        self._register_default_converters()
    
    def _register_default_converters(self) -> None:
        """Register default unit conversion functions."""
        # Temperature conversions
        self._unit_converters['celsius_to_kelvin'] = lambda c: c + 273.15
        self._unit_converters['fahrenheit_to_celsius'] = lambda f: (f - 32) * 5/9
        self._unit_converters['fahrenheit_to_kelvin'] = lambda f: (f - 32) * 5/9 + 273.15
        
        # Distance conversions
        self._unit_converters['mm_to_m'] = lambda mm: mm / 1000.0
        self._unit_converters['cm_to_m'] = lambda cm: cm / 100.0
        self._unit_converters['inches_to_m'] = lambda inches: inches * 0.0254
        
        # Angle conversions
        self._unit_converters['degrees_to_radians'] = lambda deg: deg * 3.14159265359 / 180.0
        self._unit_converters['radians_to_degrees'] = lambda rad: rad * 180.0 / 3.14159265359
    
    def register_converter(self, sensor_type: str, converter: Callable[[Any], float]) -> None:
        """
        Register a custom converter for a specific sensor type.
        
        Args:
            sensor_type: Type identifier for the sensor
            converter: Function that converts raw sensor data to normalized float
        """
        self._converters[sensor_type] = converter
    
    def normalize_sensor_value(self, sensor_type: str, raw_value: Any, 
                               unit_conversion: Optional[str] = None) -> float:
        """
        Normalize a sensor value to a standard float representation.
        
        Args:
            sensor_type: Type identifier for the sensor
            raw_value: Raw sensor data in any format
            unit_conversion: Optional unit conversion to apply
        
        Returns:
            Normalized float value
        
        Raises:
            ValueError: If value cannot be normalized
        """
        # Try custom converter first
        if sensor_type in self._converters:
            normalized = self._converters[sensor_type](raw_value)
        else:
            # Default normalization strategies
            normalized = self._default_normalize(raw_value)
        
        # Apply unit conversion if specified
        if unit_conversion and unit_conversion in self._unit_converters:
            normalized = self._unit_converters[unit_conversion](normalized)
        
        return normalized
    
    def _default_normalize(self, raw_value: Any) -> float:
        """
        Default normalization strategy for unknown sensor types.
        
        Args:
            raw_value: Raw sensor data
        
        Returns:
            Normalized float value
        
        Raises:
            ValueError: If value cannot be normalized
        """
        # Handle numeric types directly
        if isinstance(raw_value, (int, float)):
            return float(raw_value)
        
        # Handle string-encoded numbers
        if isinstance(raw_value, str):
            try:
                return float(raw_value)
            except ValueError:
                raise ValueError(f"Cannot normalize string value: {raw_value}")
        
        # Handle boolean as 0.0 or 1.0
        if isinstance(raw_value, bool):
            return 1.0 if raw_value else 0.0
        
        # Handle lists/tuples - take first element or average
        if isinstance(raw_value, (list, tuple)):
            if len(raw_value) == 0:
                raise ValueError("Cannot normalize empty list")
            if len(raw_value) == 1:
                return self._default_normalize(raw_value[0])
            # Average multiple values
            return sum(self._default_normalize(v) for v in raw_value) / len(raw_value)
        
        # Handle dict - look for common keys
        if isinstance(raw_value, dict):
            for key in ['value', 'reading', 'data', 'measurement']:
                if key in raw_value:
                    return self._default_normalize(raw_value[key])
            raise ValueError(f"Cannot normalize dict without standard keys: {raw_value}")
        
        raise ValueError(f"Cannot normalize value of type {type(raw_value)}: {raw_value}")
    
    def normalize_sensor_readings(self, raw_readings: Dict[str, Any],
                                  sensor_configs: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, float]:
        """
        Normalize a dictionary of sensor readings.
        
        Args:
            raw_readings: Dictionary of raw sensor readings
            sensor_configs: Optional configuration for each sensor (type, unit conversion)
        
        Returns:
            Dictionary of normalized sensor readings
        """
        normalized = {}
        sensor_configs = sensor_configs or {}
        
        for sensor_id, raw_value in raw_readings.items():
            config = sensor_configs.get(sensor_id, {})
            sensor_type = config.get('type', 'default')
            unit_conversion = config.get('unit_conversion')
            
            try:
                normalized[sensor_id] = self.normalize_sensor_value(
                    sensor_type, raw_value, unit_conversion
                )
            except ValueError as e:
                # Log warning but continue with other sensors
                # In production, this would use proper logging
                print(f"Warning: Failed to normalize sensor {sensor_id}: {e}")
                # Use a default value or skip
                continue
        
        return normalized


class EventType:
    """Event types for state observation."""
    STATE_CHANGE = "STATE_CHANGE"
    SENSOR_UPDATE = "SENSOR_UPDATE"
    ACTUATOR_UPDATE = "ACTUATOR_UPDATE"
    ERROR_DETECTED = "ERROR_DETECTED"
    BATTERY_LOW = "BATTERY_LOW"


class StateEvent:
    """Event representing a state change."""
    
    def __init__(self, event_type: str, robot_id: UUID, timestamp: datetime, data: Dict):
        self.event_type = event_type
        self.robot_id = robot_id
        self.timestamp = timestamp
        self.data = data


class StateStream:
    """
    Stream of robot state observations with circular buffering.
    
    Implements a thread-safe circular buffer with configurable size
    for efficient state streaming. Automatically maintains chronological
    ordering and enforces monotonicity.
    
    Requirements: 1.5, 16.5
    """
    
    def __init__(self, robot_id: UUID, buffer_size: int = 1000, sampling_rate: Optional[float] = None):
        """
        Initialize state stream.
        
        Args:
            robot_id: UUID of the robot
            buffer_size: Maximum number of states to buffer (circular buffer)
            sampling_rate: Optional sampling rate in Hz (None = no rate limiting)
        """
        self.robot_id = robot_id
        self.buffer: Deque[RobotState] = deque(maxlen=buffer_size)
        self.buffer_size = buffer_size
        self.sampling_rate = sampling_rate
        self._last_sample_time: Optional[datetime] = None
        self._lock = threading.Lock()
        self._closed = False
        self._dropped_count = 0  # Track dropped states due to rate limiting
    
    def add_state(self, state: RobotState) -> bool:
        """
        Add a state observation to the stream.
        
        Args:
            state: RobotState to add
        
        Returns:
            True if state was added, False if dropped due to rate limiting
        
        Raises:
            RuntimeError: If stream is closed
            ValueError: If timestamp violates monotonicity
        """
        if self._closed:
            raise RuntimeError("Cannot add to closed stream")
        
        # Check sampling rate
        if self.sampling_rate is not None and self._last_sample_time is not None:
            min_interval = timedelta(seconds=1.0 / self.sampling_rate)
            time_since_last = state.timestamp - self._last_sample_time
            if time_since_last < min_interval:
                self._dropped_count += 1
                return False
        
        with self._lock:
            # Validate monotonicity
            if len(self.buffer) > 0:
                last_state = self.buffer[-1]
                if state.timestamp <= last_state.timestamp:
                    raise ValueError(
                        f"State timestamp {state.timestamp} is not greater than "
                        f"last timestamp {last_state.timestamp}"
                    )
            self.buffer.append(state)
            self._last_sample_time = state.timestamp
        
        return True
    
    def get_latest(self) -> Optional[RobotState]:
        """Get the most recent state observation."""
        with self._lock:
            return self.buffer[-1] if len(self.buffer) > 0 else None
    
    def get_all(self) -> List[RobotState]:
        """Get all buffered state observations in chronological order."""
        with self._lock:
            return list(self.buffer)
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the buffer.
        
        Returns:
            Dictionary with buffer statistics
        """
        with self._lock:
            return {
                'size': len(self.buffer),
                'capacity': self.buffer_size,
                'utilization': len(self.buffer) / self.buffer_size if self.buffer_size > 0 else 0.0,
                'dropped_count': self._dropped_count,
                'sampling_rate': self.sampling_rate,
            }
    
    def close(self) -> None:
        """Close the stream."""
        self._closed = True
    
    def is_closed(self) -> bool:
        """Check if stream is closed."""
        return self._closed


class EventStream:
    """Stream of state events."""
    
    def __init__(self, robot_id: UUID, event_types: Set[str], buffer_size: int = 1000):
        self.robot_id = robot_id
        self.event_types = event_types
        self.buffer: Deque[StateEvent] = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self._closed = False
    
    def add_event(self, event: StateEvent) -> None:
        """Add an event to the stream."""
        if self._closed:
            raise RuntimeError("Cannot add to closed stream")
        
        if event.event_type in self.event_types:
            with self._lock:
                self.buffer.append(event)
    
    def get_events(self) -> List[StateEvent]:
        """Get all buffered events."""
        with self._lock:
            return list(self.buffer)
    
    def close(self) -> None:
        """Close the stream."""
        self._closed = True
    
    def is_closed(self) -> bool:
        """Check if stream is closed."""
        return self._closed


class StateHistory:
    """Historical state records for a robot."""
    
    def __init__(self, robot_id: UUID, states: List[RobotState]):
        self.robot_id = robot_id
        self.states = states
        
        # Validate chronological ordering
        for i in range(len(states) - 1):
            if states[i].timestamp >= states[i + 1].timestamp:
                raise ValueError("States must be in chronological order")
    
    def get_state_at(self, timestamp: datetime) -> Optional[RobotState]:
        """Get the state at or immediately before the given timestamp."""
        for state in reversed(self.states):
            if state.timestamp <= timestamp:
                return state
        return None
    
    def get_states_in_range(self, start: datetime, end: datetime) -> List[RobotState]:
        """Get all states within the given time range."""
        return [
            state for state in self.states
            if start <= state.timestamp <= end
        ]


class TimeRange:
    """Time range for historical queries."""
    
    def __init__(self, start: datetime, end: datetime):
        if end < start:
            raise ValueError("end must be >= start")
        self.start = start
        self.end = end


class StateObserver:
    """
    State Observer component that captures and normalizes robot state data.
    
    This component provides real-time state observation and historical queries
    for robot state data. It maintains state streams for continuous monitoring
    and supports event-based observation.
    
    Features:
    - Heterogeneous sensor data normalization
    - Circular buffering with configurable size
    - Configurable sampling rates
    - Chronological ordering enforcement
    - Thread-safe operations
    
    Interface:
    - observeState(robot_id): Create continuous state stream
    - captureSnapshot(robot_id): Get point-in-time state capture
    - subscribeToEvents(robot_id, event_types): Create event stream
    - getStateHistory(robot_id, time_range): Query historical states
    - normalizeAndRecordState(robot_id, raw_data): Normalize and record state
    
    Requirements: 1.2, 1.5, 16.5
    """
    
    def __init__(self, buffer_size: int = 1000, sampling_rate: Optional[float] = None):
        """
        Initialize the StateObserver.
        
        Args:
            buffer_size: Maximum number of states to buffer per robot
            sampling_rate: Optional default sampling rate in Hz
        """
        self.buffer_size = buffer_size
        self.sampling_rate = sampling_rate
        self._normalizer = SensorDataNormalizer()
        self._state_streams: Dict[UUID, StateStream] = {}
        self._event_streams: Dict[UUID, List[EventStream]] = {}
        self._state_history: Dict[UUID, List[RobotState]] = {}
        self._sensor_configs: Dict[UUID, Dict[str, Dict[str, str]]] = {}
        self._lock = threading.Lock()
    
    def configure_sensor_normalization(self, robot_id: UUID, 
                                      sensor_configs: Dict[str, Dict[str, str]]) -> None:
        """
        Configure sensor normalization for a specific robot.
        
        Args:
            robot_id: UUID of the robot
            sensor_configs: Dictionary mapping sensor IDs to configuration
                           Each config can contain 'type' and 'unit_conversion'
        
        Example:
            observer.configure_sensor_normalization(robot_id, {
                'temp_sensor_1': {'type': 'temperature', 'unit_conversion': 'celsius_to_kelvin'},
                'distance_sensor_1': {'type': 'distance', 'unit_conversion': 'mm_to_m'}
            })
        
        Requirements: 1.2
        """
        with self._lock:
            self._sensor_configs[robot_id] = sensor_configs
    
    def register_sensor_converter(self, sensor_type: str, 
                                  converter: Callable[[Any], float]) -> None:
        """
        Register a custom converter for a specific sensor type.
        
        Args:
            sensor_type: Type identifier for the sensor
            converter: Function that converts raw sensor data to normalized float
        
        Requirements: 1.2
        """
        self._normalizer.register_converter(sensor_type, converter)
    
    def normalizeAndRecordState(self, robot_id: UUID, raw_data: Dict[str, Any]) -> RobotState:
        """
        Normalize raw sensor data and record the resulting state.
        
        This method handles heterogeneous sensor data formats, normalizes them
        into a unified RobotState representation, and records the state in the
        observation stream.
        
        Args:
            robot_id: UUID of the robot
            raw_data: Dictionary containing raw state data with keys:
                     - timestamp: datetime
                     - position: Vector3D or dict with x, y, z
                     - orientation: Quaternion or dict with w, x, y, z
                     - joint_states: dict of joint data
                     - sensor_readings: dict of raw sensor values
                     - actuator_states: dict of actuator data
                     - battery_level: float (0.0-1.0)
                     - error_flags: set of error codes
        
        Returns:
            Normalized RobotState
        
        Requirements: 1.2, 1.5
        """
        # Normalize sensor readings
        sensor_configs = self._sensor_configs.get(robot_id, {})
        normalized_sensors = self._normalizer.normalize_sensor_readings(
            raw_data.get('sensor_readings', {}),
            sensor_configs
        )
        
        # Normalize position if needed
        position_data = raw_data.get('position')
        if isinstance(position_data, dict):
            position = Vector3D(
                position_data.get('x', 0.0),
                position_data.get('y', 0.0),
                position_data.get('z', 0.0)
            )
        elif isinstance(position_data, Vector3D):
            position = position_data
        else:
            raise ValueError("position must be Vector3D or dict with x, y, z")
        
        # Normalize orientation if needed
        orientation_data = raw_data.get('orientation')
        if isinstance(orientation_data, dict):
            orientation = Quaternion(
                orientation_data.get('w', 1.0),
                orientation_data.get('x', 0.0),
                orientation_data.get('y', 0.0),
                orientation_data.get('z', 0.0)
            )
        elif isinstance(orientation_data, Quaternion):
            orientation = orientation_data
        else:
            raise ValueError("orientation must be Quaternion or dict with w, x, y, z")
        
        # Normalize joint states if needed
        joint_states_data = raw_data.get('joint_states', {})
        joint_states = {}
        for joint_id, joint_data in joint_states_data.items():
            if isinstance(joint_data, JointState):
                joint_states[joint_id] = joint_data
            elif isinstance(joint_data, dict):
                joint_states[joint_id] = JointState(
                    joint_id=joint_id,
                    angle=joint_data.get('angle', 0.0),
                    velocity=joint_data.get('velocity', 0.0),
                    torque=joint_data.get('torque', 0.0),
                    temperature=joint_data.get('temperature', 25.0)
                )
            else:
                raise ValueError(f"Invalid joint state data for {joint_id}")
        
        # Create normalized RobotState
        state = RobotState(
            robot_id=robot_id,
            timestamp=raw_data['timestamp'],
            position=position,
            orientation=orientation,
            joint_states=joint_states,
            sensor_readings=normalized_sensors,
            actuator_states=raw_data.get('actuator_states', {}),
            battery_level=raw_data.get('battery_level', 1.0),
            error_flags=raw_data.get('error_flags', set()),
            metadata=raw_data.get('metadata', {})
        )
        
        # Record the normalized state
        self._record_state(state)
        
        return state
    
    def observeState(self, robot_id: UUID, sampling_rate: Optional[float] = None) -> StateStream:
        """
        Create a continuous state observation stream for a robot.
        
        This method creates a StateStream that will receive all state updates
        for the specified robot. The stream maintains a circular buffer of
        recent states with configurable size.
        
        Args:
            robot_id: UUID of the robot to observe
            sampling_rate: Optional sampling rate in Hz (overrides default)
        
        Returns:
            StateStream for continuous state observation
        
        Requirements: 1.1, 1.2, 16.1, 16.5
        """
        with self._lock:
            if robot_id not in self._state_streams:
                rate = sampling_rate if sampling_rate is not None else self.sampling_rate
                self._state_streams[robot_id] = StateStream(robot_id, self.buffer_size, rate)
            return self._state_streams[robot_id]
    
    def captureSnapshot(self, robot_id: UUID) -> Optional[RobotState]:
        """
        Capture a point-in-time snapshot of robot state.
        
        This method returns the most recent state observation for the robot.
        If no state has been observed yet, returns None.
        
        Args:
            robot_id: UUID of the robot
        
        Returns:
            Most recent RobotState or None if no state available
        
        Requirements: 1.1, 1.2
        """
        with self._lock:
            # Check state history first (most reliable source)
            if robot_id in self._state_history and len(self._state_history[robot_id]) > 0:
                return self._state_history[robot_id][-1]
            
            # Fall back to state stream
            if robot_id in self._state_streams:
                return self._state_streams[robot_id].get_latest()
            
            return None
    
    def subscribeToEvents(self, robot_id: UUID, event_types: Set[str]) -> EventStream:
        """
        Subscribe to specific event types for a robot.
        
        This method creates an EventStream that will receive only events
        matching the specified event types. Multiple event streams can be
        created for the same robot with different event type filters.
        
        Args:
            robot_id: UUID of the robot
            event_types: Set of event type strings to subscribe to
        
        Returns:
            EventStream for event-based observation
        
        Requirements: 1.1, 16.1
        """
        with self._lock:
            event_stream = EventStream(robot_id, event_types, self.buffer_size)
            if robot_id not in self._event_streams:
                self._event_streams[robot_id] = []
            self._event_streams[robot_id].append(event_stream)
            return event_stream
    
    def getStateHistory(self, robot_id: UUID, time_range: TimeRange) -> StateHistory:
        """
        Query historical state records for a robot within a time range.
        
        This method returns all state observations for the robot within the
        specified time range. States are guaranteed to be in chronological
        order with no gaps in the timeline.
        
        Args:
            robot_id: UUID of the robot
            time_range: TimeRange specifying start and end times
        
        Returns:
            StateHistory containing all states in the time range
        
        Requirements: 1.4, 1.5, 16.2, 16.3, 16.4
        """
        with self._lock:
            if robot_id not in self._state_history:
                return StateHistory(robot_id, [])
            
            all_states = self._state_history[robot_id]
            filtered_states = [
                state for state in all_states
                if time_range.start <= state.timestamp <= time_range.end
            ]
            
            return StateHistory(robot_id, filtered_states)
    
    def _record_state(self, state: RobotState) -> None:
        """
        Internal method to record a state observation.
        
        This method adds the state to the appropriate stream and historical
        records. It validates monotonicity and triggers event generation.
        
        Args:
            state: RobotState to record
        """
        with self._lock:
            robot_id = state.robot_id
            
            # Add to state stream
            if robot_id in self._state_streams:
                self._state_streams[robot_id].add_state(state)
            
            # Add to historical records
            if robot_id not in self._state_history:
                self._state_history[robot_id] = []
            
            # Validate monotonicity
            if len(self._state_history[robot_id]) > 0:
                last_state = self._state_history[robot_id][-1]
                if state.timestamp <= last_state.timestamp:
                    raise ValueError(
                        f"State timestamp {state.timestamp} is not greater than "
                        f"last timestamp {last_state.timestamp}"
                    )
            
            self._state_history[robot_id].append(state)
            
            # Generate and distribute events
            self._generate_events(state)
    
    def _generate_events(self, state: RobotState) -> None:
        """
        Generate events from state observation.
        
        This method analyzes the state and generates appropriate events
        (e.g., battery low, error detected) which are distributed to
        subscribed event streams.
        
        Args:
            state: RobotState to analyze for events
        """
        robot_id = state.robot_id
        
        if robot_id not in self._event_streams:
            return
        
        events = []
        
        # Generate state change event
        events.append(StateEvent(
            EventType.STATE_CHANGE,
            robot_id,
            state.timestamp,
            {"state": state}
        ))
        
        # Generate battery low event if needed
        if state.battery_level < 0.2:
            events.append(StateEvent(
                EventType.BATTERY_LOW,
                robot_id,
                state.timestamp,
                {"battery_level": state.battery_level}
            ))
        
        # Generate error event if error flags present
        if len(state.error_flags) > 0:
            events.append(StateEvent(
                EventType.ERROR_DETECTED,
                robot_id,
                state.timestamp,
                {"error_flags": state.error_flags}
            ))
        
        # Distribute events to subscribed streams
        for event in events:
            for event_stream in self._event_streams[robot_id]:
                if not event_stream.is_closed():
                    event_stream.add_event(event)
    
    def close_stream(self, robot_id: UUID) -> None:
        """
        Close all streams for a robot.
        
        Args:
            robot_id: UUID of the robot
        """
        with self._lock:
            if robot_id in self._state_streams:
                self._state_streams[robot_id].close()
            
            if robot_id in self._event_streams:
                for event_stream in self._event_streams[robot_id]:
                    event_stream.close()
