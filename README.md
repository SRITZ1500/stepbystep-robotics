# StepbyStep:ROBOTICS

Comprehensive observability and translation system that makes robots legible, operable, and improvable.

## Overview

StepbyStep:ROBOTICS provides three interconnected layers:

- **Behavior Layer**: Real-time state observation and action translation for robot legibility
- **Workflow Layer**: Runbook management, task specifications, and execution tracking for operability
- **Improvement Layer**: Evaluation, regression detection, and governance for continuous enhancement

## Project Structure

```
src/stepbystep_robotics/
├── __init__.py           # Package initialization
├── models.py             # Core data models
├── behavior/             # Behavior Layer components
├── workflow/             # Workflow Layer components
└── improvement/          # Improvement Layer components

tests/
├── test_models.py        # Unit tests for data models
└── test_models_properties.py  # Property-based tests
```

## Core Data Models

### RobotState
Normalized representation of robot state at a point in time, including:
- Position and orientation
- Joint states
- Sensor readings
- Actuator states
- Battery level
- Error flags

### TaskSpecification
Formal task definition with:
- Preconditions and postconditions
- Execution steps
- Safety constraints
- Required capabilities
- Timeout configuration

### ExecutionTrace
Complete record of task execution including:
- All execution steps
- State history
- Performance metrics
- Detected anomalies

### PerformanceMetrics
Performance analysis results with:
- Duration and success rate
- Energy consumption
- Accuracy, smoothness, and safety scores
- Per-step metrics

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests
pytest tests/test_models.py

# Run only property-based tests
pytest tests/test_models_properties.py
```

## Development

This project uses:
- **pytest** for unit testing
- **hypothesis** for property-based testing
- **Python 3.9+** as the minimum version

## Validation Rules

All data models include comprehensive validation:
- Type checking for all fields
- Range validation for numeric values
- Uniqueness constraints for identifiers
- Chronological ordering for time-based data
- Non-empty requirements for critical fields

## License

Copyright (c) 2024. All rights reserved.
