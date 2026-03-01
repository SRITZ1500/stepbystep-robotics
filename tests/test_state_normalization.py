"""
Unit tests for state normalization and buffering features.

Tests verify:
- Sensor data normalization from heterogeneous formats
- Unit conversions
- Custom converter registration
- Circular buffer with configurable size
- Sampling rate enforcement
- Buffer statistics
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
    SensorDataNormalizer,
)


class TestSensorDataNormalizer:
    """Test suite for SensorDataNormalizer."""
    
    def test_normalize_numeric_value(self):
        """Test normalization of numeric values."""
        normalizer = SensorDataNormalizer()
        
        # Integer
        assert normalizer.normalize_sensor_value('default', 42) == 42.0
        
        # Float
        assert normalizer.normalize_sensor_value('default', 3.14) == 3.14
    
    def test_normalize_string_value(self):
        """Test normalization of string-encoded numbers."""
        normalizer = SensorDataNormalizer()
        
        assert normalizer.normalize_sensor_value('default', '42.5') == 42.5
        assert normalizer.normalize_sensor_value('default', '100') == 100.0
    
    def test_normalize_boolean_value(self):
        """Test normalization of boolean values."""
        normalizer = SensorDataNormalizer()
        
        assert normalizer.normalize_sensor_value('default', True) == 1.0
        assert normalizer.normalize_sensor_value('default', False) == 0.0
    
    def test_normalize_list_value(self):
        """Test normalization of list values."""
        normalizer = SensorDataNormalizer()
        
        # Single element
        assert normalizer.normalize_sensor_value('default', [42.0]) == 42.0
        
        # Multiple elements (average)
        assert normalizer.normalize_sensor_value('default', [10.0, 20.0, 30.0]) == 20.0
    
    def test_normalize_dict_value(self):
        """Test normalization of dict values with standard keys."""
        normalizer = SensorDataNormalizer()
        
        assert normalizer.normalize_sensor_value('default', {'value': 42.0}) == 42.0
        assert normalizer.normalize_sensor_value('default', {'reading': 3.14}) == 3.14
        assert normalizer.normalize_sensor_value('default', {'data': 100.0}) == 100.0
    
    def test_normalize_invalid_string_raises_error(self):
        """Test that invalid string values raise ValueError."""
        normalizer = SensorDataNormalizer()
        
        with pytest.raises(ValueError, match="Cannot normalize string value"):
            normalizer.normalize_sensor_value('default', 'not_a_number')
    
    def test_normalize_empty_list_raises_error(self):
        """Test that empty list raises ValueError."""
        normalizer = SensorDataNormalizer()
        
        with pytest.raises(ValueError, match="Cannot normalize empty list"):
            normalizer.normalize_sensor_value('default', [])
    
    def test_normalize_dict_without_standard_keys_raises_error(self):
        """Test that dict without standard keys raises ValueError."""
        normalizer = SensorDataNormalizer()
        
        with pytest.raises(ValueError, match="Cannot normalize dict"):
            normalizer.normalize_sensor_value('default', {'unknown_key': 42.0})
    
    def test_unit_conversion_temperature(self):
        """Test temperature unit conversions."""
        normalizer = SensorDataNormalizer()
        
        # Celsius to Kelvin
        result = normalizer.normalize_sensor_value('default', 0.0, 'celsius_to_kelvin')
        assert abs(result - 273.15) < 0.01
        
        # Fahrenheit to Celsius
        result = normalizer.normalize_sensor_value('default', 32.0, 'fahrenheit_to_celsius')
        assert abs(result - 0.0) < 0.01
    
    def test_unit_conversion_distance(self):
        """Test distance unit conversions."""
        normalizer = SensorDataNormalizer()
        
        # Millimeters to meters
        result = normalizer.normalize_sensor_value('default', 1000.0, 'mm_to_m')
        assert abs(result - 1.0) < 0.01
        
        # Centimeters to meters
        result = normalizer.normalize_sensor_value('default', 100.0, 'cm_to_m')
        assert abs(result - 1.0) < 0.01
    
    def test_unit_conversion_angle(self):
        """Test angle unit conversions."""
        normalizer = SensorDataNormalizer()
        
        # Degrees to radians
        result = normalizer.normalize_sensor_value('default', 180.0, 'degrees_to_radians')
        assert abs(result - 3.14159265359) < 0.01
    
    def test_register_custom_converter(self):
        """Test registering custom converter for specific sensor type."""
        normalizer = SensorDataNormalizer()
        
        # Register custom converter that doubles the value
        normalizer.register_converter('custom_sensor', lambda x: float(x) * 2.0)
        
        result = normalizer.normalize_sensor_value('custom_sensor', 21.0)
        assert result == 42.0
    
    def test_normalize_sensor_readings_dict(self):
        """Test normalizing a dictionary of sensor readings."""
        normalizer = SensorDataNormalizer()
        
        raw_readings = {
            'sensor1': 42,
            'sensor2': '3.14',
            'sensor3': True,
            'sensor4': [10.0, 20.0],
        }
        
        normalized = normalizer.normalize_sensor_readings(raw_readings)
        
        assert normalized['sensor1'] == 42.0
        assert normalized['sensor2'] == 3.14
        assert normalized['sensor3'] == 1.0
        assert normalized['sensor4'] == 15.0  # Average
    
    def test_normalize_sensor_readings_with_config(self):
        """Test normalizing sensor readings with configuration."""
        normalizer = SensorDataNormalizer()
        
        raw_readings = {
            'temp_sensor': 25.0,
            'distance_sensor': 1000.0,
        }
        
        sensor_configs = {
            'temp_sensor': {'type': 'temperature', 'unit_conversion': 'celsius_to_kelvin'},
            'distance_sensor': {'type': 'distance', 'unit_conversion': 'mm_to_m'},
        }
        
        normalized = normalizer.normalize_sensor_readings(raw_readings, sensor_configs)
        
        assert abs(normalized['temp_sensor'] - 298.15) < 0.01
        assert abs(normalized['distance_sensor'] - 1.0) < 0.01
    
    def test_normalize_sensor_readings_skips_invalid(self):
        """Test that invalid sensor readings are skipped with warning."""
        normalizer = SensorDataNormalizer()
        
        raw_readings = {
            'valid_sensor': 42.0,
            'invalid_sensor': {'no_standard_key': 'value'},
        }
        
        # Should not raise, just skip invalid sensor
        normalized = normalizer.normalize_sensor_readings(raw_readings)
        
        assert 'valid_sensor' in normalized
        assert 'invalid_sensor' not in normalized


class TestStateStreamBuffering:
    """Test suite for StateStream buffering features."""
    
    def create_test_state(self, robot_id, timestamp):
        """Helper to create a test robot state."""
        return RobotState(
            robot_id=robot_id,
            timestamp=timestamp,
            position=Vector3D(1.0, 2.0, 3.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 0.0),
            joint_states={},
            sensor_readings={},
            actuator_states={},
            battery_level=0.8,
            error_flags=set(),
        )
    
    def test_circular_buffer_respects_size_limit(self):
        """Test that circular buffer respects configured size limit."""
        observer = StateObserver(buffer_size=5)
        robot_id = uuid4()
        
        stream = observer.observeState(robot_id)
        
        base_time = datetime.now()
        
        # Add more states than buffer size
        for i in range(10):
            state = self.create_test_state(robot_id, base_time + timedelta(seconds=i))
            observer._record_state(state)
        
        all_states = stream.get_all()
        
        # Should only have last 5 states
        assert len(all_states) == 5
        # Should have states 5-9
        assert all_states[0].timestamp == base_time + timedelta(seconds=5)
        assert all_states[-1].timestamp == base_time + timedelta(seconds=9)
    
    def test_sampling_rate_enforcement(self):
        """Test that sampling rate is enforced."""
        observer = StateObserver(buffer_size=100)
        robot_id = uuid4()
        
        # Create stream with 10 Hz sampling rate (100ms interval)
        stream = observer.observeState(robot_id, sampling_rate=10.0)
        
        base_time = datetime.now()
        
        # Try to add states at 50ms intervals (20 Hz)
        added_count = 0
        for i in range(10):
            state = self.create_test_state(robot_id, base_time + timedelta(milliseconds=i * 50))
            if stream.add_state(state):
                added_count += 1
        
        # Should have dropped about half the states
        assert added_count <= 6  # Allow some tolerance
        assert stream.get_buffer_stats()['dropped_count'] > 0
    
    def test_buffer_stats(self):
        """Test buffer statistics reporting."""
        observer = StateObserver(buffer_size=10)
        robot_id = uuid4()
        
        stream = observer.observeState(robot_id, sampling_rate=5.0)
        
        base_time = datetime.now()
        
        # Add 5 states
        for i in range(5):
            state = self.create_test_state(robot_id, base_time + timedelta(seconds=i))
            stream.add_state(state)
        
        stats = stream.get_buffer_stats()
        
        assert stats['size'] == 5
        assert stats['capacity'] == 10
        assert stats['utilization'] == 0.5
        assert stats['sampling_rate'] == 5.0
    
    def test_chronological_ordering_maintained(self):
        """Test that chronological ordering is maintained in buffer."""
        observer = StateObserver(buffer_size=100)
        robot_id = uuid4()
        
        stream = observer.observeState(robot_id)
        
        base_time = datetime.now()
        
        # Add states
        for i in range(10):
            state = self.create_test_state(robot_id, base_time + timedelta(seconds=i))
            observer._record_state(state)
        
        all_states = stream.get_all()
        
        # Verify chronological ordering
        for i in range(len(all_states) - 1):
            assert all_states[i].timestamp < all_states[i + 1].timestamp


class TestStateObserverNormalization:
    """Test suite for StateObserver normalization integration."""
    
    def test_configure_sensor_normalization(self):
        """Test configuring sensor normalization for a robot."""
        observer = StateObserver()
        robot_id = uuid4()
        
        sensor_configs = {
            'temp_sensor': {'type': 'temperature', 'unit_conversion': 'celsius_to_kelvin'},
            'distance_sensor': {'type': 'distance', 'unit_conversion': 'mm_to_m'},
        }
        
        observer.configure_sensor_normalization(robot_id, sensor_configs)
        
        # Verify configuration is stored
        assert robot_id in observer._sensor_configs
        assert observer._sensor_configs[robot_id] == sensor_configs
    
    def test_register_sensor_converter(self):
        """Test registering custom sensor converter."""
        observer = StateObserver()
        
        # Register custom converter
        observer.register_sensor_converter('custom_type', lambda x: float(x) * 10.0)
        
        # Verify converter is registered
        assert 'custom_type' in observer._normalizer._converters
    
    def test_normalize_and_record_state(self):
        """Test normalizing and recording state from raw data."""
        observer = StateObserver()
        robot_id = uuid4()
        
        # Configure sensor normalization
        observer.configure_sensor_normalization(robot_id, {
            'temp_sensor': {'type': 'temperature', 'unit_conversion': 'celsius_to_kelvin'},
        })
        
        # Create raw data with heterogeneous formats
        raw_data = {
            'timestamp': datetime.now(),
            'position': {'x': 1.0, 'y': 2.0, 'z': 3.0},
            'orientation': {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0},
            'joint_states': {
                'joint1': {'angle': 0.5, 'velocity': 0.1, 'torque': 0.2, 'temperature': 25.0}
            },
            'sensor_readings': {
                'temp_sensor': 25.0,  # Celsius, will be converted to Kelvin
                'pressure_sensor': '101.3',  # String, will be converted to float
                'status_sensor': True,  # Boolean, will be converted to 1.0
            },
            'actuator_states': {'motor1': 'active'},
            'battery_level': 0.85,
            'error_flags': set(),
        }
        
        state = observer.normalizeAndRecordState(robot_id, raw_data)
        
        # Verify state was created correctly
        assert state.robot_id == robot_id
        assert state.position.x == 1.0
        assert state.position.y == 2.0
        assert state.position.z == 3.0
        assert state.battery_level == 0.85
        
        # Verify sensor normalization
        assert abs(state.sensor_readings['temp_sensor'] - 298.15) < 0.01  # Converted to Kelvin
        assert state.sensor_readings['pressure_sensor'] == 101.3  # Converted from string
        assert state.sensor_readings['status_sensor'] == 1.0  # Converted from boolean
        
        # Verify joint state normalization
        assert 'joint1' in state.joint_states
        assert state.joint_states['joint1'].angle == 0.5
        
        # Verify state was recorded
        snapshot = observer.captureSnapshot(robot_id)
        assert snapshot is not None
        assert snapshot.timestamp == state.timestamp
    
    def test_normalize_and_record_with_vector3d_objects(self):
        """Test normalization with Vector3D and Quaternion objects."""
        observer = StateObserver()
        robot_id = uuid4()
        
        raw_data = {
            'timestamp': datetime.now(),
            'position': Vector3D(1.0, 2.0, 3.0),
            'orientation': Quaternion(1.0, 0.0, 0.0, 0.0),
            'joint_states': {},
            'sensor_readings': {},
            'actuator_states': {},
            'battery_level': 0.9,
            'error_flags': set(),
        }
        
        state = observer.normalizeAndRecordState(robot_id, raw_data)
        
        assert state.position.x == 1.0
        assert state.orientation.w == 1.0
    
    def test_normalize_and_record_with_joint_state_objects(self):
        """Test normalization with JointState objects."""
        observer = StateObserver()
        robot_id = uuid4()
        
        raw_data = {
            'timestamp': datetime.now(),
            'position': Vector3D(1.0, 2.0, 3.0),
            'orientation': Quaternion(1.0, 0.0, 0.0, 0.0),
            'joint_states': {
                'joint1': JointState('joint1', 0.5, 0.1, 0.2, 25.0)
            },
            'sensor_readings': {},
            'actuator_states': {},
            'battery_level': 0.9,
            'error_flags': set(),
        }
        
        state = observer.normalizeAndRecordState(robot_id, raw_data)
        
        assert 'joint1' in state.joint_states
        assert state.joint_states['joint1'].angle == 0.5
    
    def test_normalize_and_record_invalid_position_raises_error(self):
        """Test that invalid position data raises ValueError."""
        observer = StateObserver()
        robot_id = uuid4()
        
        raw_data = {
            'timestamp': datetime.now(),
            'position': 'invalid',  # Invalid type
            'orientation': Quaternion(1.0, 0.0, 0.0, 0.0),
            'joint_states': {},
            'sensor_readings': {},
            'actuator_states': {},
            'battery_level': 0.9,
            'error_flags': set(),
        }
        
        with pytest.raises(ValueError, match="position must be"):
            observer.normalizeAndRecordState(robot_id, raw_data)
    
    def test_normalize_and_record_invalid_orientation_raises_error(self):
        """Test that invalid orientation data raises ValueError."""
        observer = StateObserver()
        robot_id = uuid4()
        
        raw_data = {
            'timestamp': datetime.now(),
            'position': Vector3D(1.0, 2.0, 3.0),
            'orientation': 'invalid',  # Invalid type
            'joint_states': {},
            'sensor_readings': {},
            'actuator_states': {},
            'battery_level': 0.9,
            'error_flags': set(),
        }
        
        with pytest.raises(ValueError, match="orientation must be"):
            observer.normalizeAndRecordState(robot_id, raw_data)
