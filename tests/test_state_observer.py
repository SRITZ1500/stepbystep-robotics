"""
Unit tests for StateObserver component.

Tests verify:
- State stream creation and observation
- Snapshot capture
- Event subscription and filtering
- Historical state queries
- Monotonicity validation
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.stepbystep_robotics.models import (
    RobotState,
    Vector3D,
    Quaternion,
    JointState,
)
from src.stepbystep_robotics.behavior import (
    StateObserver,
    TimeRange,
    EventType,
)


def create_test_robot_state(robot_id, timestamp, battery_level=0.8, error_flags=None):
    """Helper to create a test robot state."""
    return RobotState(
        robot_id=robot_id,
        timestamp=timestamp,
        position=Vector3D(1.0, 2.0, 3.0),
        orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
        joint_states={
            "joint1": JointState("joint1", 0.5, 0.1, 0.2, 25.0)
        },
        sensor_readings={"sensor1": 42.0},
        actuator_states={"actuator1": "active"},
        battery_level=battery_level,
        error_flags=error_flags or set(),
    )


class TestStateObserver:
    """Test suite for StateObserver component."""
    
    def test_observe_state_creates_stream(self):
        """Test that observeState creates a state stream."""
        observer = StateObserver()
        robot_id = uuid4()
        
        stream = observer.observeState(robot_id)
        
        assert stream is not None
        assert stream.robot_id == robot_id
        assert not stream.is_closed()
    
    def test_observe_state_returns_same_stream(self):
        """Test that multiple calls return the same stream."""
        observer = StateObserver()
        robot_id = uuid4()
        
        stream1 = observer.observeState(robot_id)
        stream2 = observer.observeState(robot_id)
        
        assert stream1 is stream2
    
    def test_capture_snapshot_returns_none_initially(self):
        """Test that captureSnapshot returns None when no state recorded."""
        observer = StateObserver()
        robot_id = uuid4()
        
        snapshot = observer.captureSnapshot(robot_id)
        
        assert snapshot is None
    
    def test_capture_snapshot_returns_latest_state(self):
        """Test that captureSnapshot returns the most recent state."""
        observer = StateObserver()
        robot_id = uuid4()
        
        # Record states
        state1 = create_test_robot_state(robot_id, datetime.now())
        state2 = create_test_robot_state(robot_id, datetime.now() + timedelta(seconds=1))
        
        observer._record_state(state1)
        observer._record_state(state2)
        
        snapshot = observer.captureSnapshot(robot_id)
        
        assert snapshot is not None
        assert snapshot.timestamp == state2.timestamp
    
    def test_subscribe_to_events_creates_event_stream(self):
        """Test that subscribeToEvents creates an event stream."""
        observer = StateObserver()
        robot_id = uuid4()
        event_types = {EventType.STATE_CHANGE, EventType.BATTERY_LOW}
        
        event_stream = observer.subscribeToEvents(robot_id, event_types)
        
        assert event_stream is not None
        assert event_stream.robot_id == robot_id
        assert event_stream.event_types == event_types
        assert not event_stream.is_closed()
    
    def test_subscribe_to_events_filters_by_type(self):
        """Test that event streams only receive subscribed event types."""
        observer = StateObserver()
        robot_id = uuid4()
        
        # Subscribe to only battery events
        event_stream = observer.subscribeToEvents(robot_id, {EventType.BATTERY_LOW})
        
        # Record state with low battery
        state = create_test_robot_state(robot_id, datetime.now(), battery_level=0.1)
        observer._record_state(state)
        
        events = event_stream.get_events()
        
        # Should only have battery low event, not state change event
        assert len(events) == 1
        assert events[0].event_type == EventType.BATTERY_LOW
    
    def test_get_state_history_empty_initially(self):
        """Test that getStateHistory returns empty history initially."""
        observer = StateObserver()
        robot_id = uuid4()
        
        now = datetime.now()
        time_range = TimeRange(now - timedelta(hours=1), now)
        
        history = observer.getStateHistory(robot_id, time_range)
        
        assert history.robot_id == robot_id
        assert len(history.states) == 0
    
    def test_get_state_history_returns_states_in_range(self):
        """Test that getStateHistory returns only states within time range."""
        observer = StateObserver()
        robot_id = uuid4()
        
        base_time = datetime.now()
        
        # Record states at different times
        state1 = create_test_robot_state(robot_id, base_time)
        state2 = create_test_robot_state(robot_id, base_time + timedelta(seconds=10))
        state3 = create_test_robot_state(robot_id, base_time + timedelta(seconds=20))
        state4 = create_test_robot_state(robot_id, base_time + timedelta(seconds=30))
        
        observer._record_state(state1)
        observer._record_state(state2)
        observer._record_state(state3)
        observer._record_state(state4)
        
        # Query for middle range
        time_range = TimeRange(
            base_time + timedelta(seconds=5),
            base_time + timedelta(seconds=25)
        )
        
        history = observer.getStateHistory(robot_id, time_range)
        
        assert len(history.states) == 2
        assert history.states[0].timestamp == state2.timestamp
        assert history.states[1].timestamp == state3.timestamp
    
    def test_record_state_validates_monotonicity(self):
        """Test that _record_state enforces monotonically increasing timestamps."""
        observer = StateObserver()
        robot_id = uuid4()
        
        base_time = datetime.now()
        
        state1 = create_test_robot_state(robot_id, base_time)
        state2 = create_test_robot_state(robot_id, base_time)  # Same timestamp
        
        observer._record_state(state1)
        
        with pytest.raises(ValueError, match="not greater than"):
            observer._record_state(state2)
    
    def test_record_state_generates_error_event(self):
        """Test that _record_state generates error events when error flags present."""
        observer = StateObserver()
        robot_id = uuid4()
        
        # Subscribe to error events
        event_stream = observer.subscribeToEvents(robot_id, {EventType.ERROR_DETECTED})
        
        # Record state with error flags
        state = create_test_robot_state(
            robot_id,
            datetime.now(),
            error_flags={"MOTOR_FAULT", "SENSOR_TIMEOUT"}
        )
        observer._record_state(state)
        
        events = event_stream.get_events()
        
        assert len(events) == 1
        assert events[0].event_type == EventType.ERROR_DETECTED
        assert "error_flags" in events[0].data
    
    def test_state_stream_maintains_buffer_size(self):
        """Test that state stream respects buffer size limit."""
        observer = StateObserver(buffer_size=5)
        robot_id = uuid4()
        
        stream = observer.observeState(robot_id)
        
        base_time = datetime.now()
        
        # Record more states than buffer size
        for i in range(10):
            state = create_test_robot_state(robot_id, base_time + timedelta(seconds=i))
            observer._record_state(state)
        
        all_states = stream.get_all()
        
        # Should only have last 5 states
        assert len(all_states) == 5
    
    def test_close_stream_closes_all_streams(self):
        """Test that close_stream closes state and event streams."""
        observer = StateObserver()
        robot_id = uuid4()
        
        state_stream = observer.observeState(robot_id)
        event_stream = observer.subscribeToEvents(robot_id, {EventType.STATE_CHANGE})
        
        observer.close_stream(robot_id)
        
        assert state_stream.is_closed()
        assert event_stream.is_closed()
    
    def test_time_range_validates_start_before_end(self):
        """Test that TimeRange validates start <= end."""
        now = datetime.now()
        
        # Valid range
        time_range = TimeRange(now - timedelta(hours=1), now)
        assert time_range.start < time_range.end
        
        # Invalid range
        with pytest.raises(ValueError, match="end must be >= start"):
            TimeRange(now, now - timedelta(hours=1))
    
    def test_state_history_validates_chronological_order(self):
        """Test that StateHistory validates chronological ordering."""
        from src.stepbystep_robotics.behavior.state_observer import StateHistory
        
        robot_id = uuid4()
        base_time = datetime.now()
        
        state1 = create_test_robot_state(robot_id, base_time)
        state2 = create_test_robot_state(robot_id, base_time + timedelta(seconds=1))
        
        # Valid order
        history = StateHistory(robot_id, [state1, state2])
        assert len(history.states) == 2
        
        # Invalid order
        with pytest.raises(ValueError, match="chronological order"):
            StateHistory(robot_id, [state2, state1])
    
    def test_state_history_get_state_at(self):
        """Test StateHistory.get_state_at returns correct state."""
        from src.stepbystep_robotics.behavior.state_observer import StateHistory
        
        robot_id = uuid4()
        base_time = datetime.now()
        
        state1 = create_test_robot_state(robot_id, base_time)
        state2 = create_test_robot_state(robot_id, base_time + timedelta(seconds=10))
        state3 = create_test_robot_state(robot_id, base_time + timedelta(seconds=20))
        
        history = StateHistory(robot_id, [state1, state2, state3])
        
        # Query at exact timestamp
        result = history.get_state_at(base_time + timedelta(seconds=10))
        assert result.timestamp == state2.timestamp
        
        # Query between timestamps (should return earlier state)
        result = history.get_state_at(base_time + timedelta(seconds=15))
        assert result.timestamp == state2.timestamp
        
        # Query before all states
        result = history.get_state_at(base_time - timedelta(seconds=5))
        assert result is None
