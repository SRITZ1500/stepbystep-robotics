"""
Tests for Runbook Manager

Validates runbook creation, validation, execution coordination, and usage tracking.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.stepbystep_robotics.workflow.runbook_manager import (
    RunbookManager,
    Runbook,
    RunbookStep,
    RunbookExecution,
    RunbookUsageStats,
    ValidationReport
)


@pytest.fixture
def runbook_manager():
    """Create a runbook manager for testing"""
    manager = RunbookManager()
    # Register some test tasks
    manager.register_task("task-1")
    manager.register_task("task-2")
    manager.register_task("task-3")
    return manager


@pytest.fixture
def simple_steps():
    """Create simple runbook steps"""
    return [
        RunbookStep(
            step_number=1,
            task_id="task-1",
            description="First step"
        ),
        RunbookStep(
            step_number=2,
            task_id="task-2",
            description="Second step",
            dependencies={1}
        ),
        RunbookStep(
            step_number=3,
            task_id="task-3",
            description="Third step",
            dependencies={2}
        )
    ]


def test_runbook_manager_initialization(runbook_manager):
    """Test runbook manager initializes correctly"""
    assert len(runbook_manager.runbooks) == 0
    assert len(runbook_manager.executions) == 0
    assert len(runbook_manager.usage_stats) == 0


def test_register_task(runbook_manager):
    """Test registering tasks"""
    runbook_manager.register_task("new-task")
    assert "new-task" in runbook_manager.task_registry


def test_create_runbook(runbook_manager, simple_steps):
    """Test creating a runbook"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="A test runbook",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    assert runbook_id in runbook_manager.runbooks
    runbook = runbook_manager.runbooks[runbook_id]
    assert runbook.name == "Test Runbook"
    assert runbook.version == 1
    assert len(runbook.steps) == 3


def test_create_runbook_with_tags(runbook_manager, simple_steps):
    """Test creating a runbook with tags"""
    tags = {"safety", "production"}
    runbook_id = runbook_manager.create_runbook(
        name="Tagged Runbook",
        description="A runbook with tags",
        steps=simple_steps,
        created_by="operator-123",
        tags=tags
    )
    
    runbook = runbook_manager.runbooks[runbook_id]
    assert runbook.tags == tags


def test_create_runbook_empty_name(runbook_manager, simple_steps):
    """Test that empty name raises ValueError"""
    with pytest.raises(ValueError, match="name cannot be empty"):
        runbook_manager.create_runbook(
            name="",
            description="Test",
            steps=simple_steps,
            created_by="operator-123"
        )


def test_create_runbook_empty_steps(runbook_manager):
    """Test that empty steps raises ValueError"""
    with pytest.raises(ValueError, match="at least one step"):
        runbook_manager.create_runbook(
            name="Empty Runbook",
            description="Test",
            steps=[],
            created_by="operator-123"
        )


def test_create_runbook_invalid_task_reference(runbook_manager):
    """Test that referencing unknown task raises ValueError"""
    steps = [
        RunbookStep(
            step_number=1,
            task_id="unknown-task",
            description="Invalid step"
        )
    ]
    
    with pytest.raises(ValueError, match="validation failed"):
        runbook_manager.create_runbook(
            name="Invalid Runbook",
            description="Test",
            steps=steps,
            created_by="operator-123"
        )


def test_create_runbook_circular_dependency(runbook_manager):
    """Test that circular dependencies are detected"""
    steps = [
        RunbookStep(
            step_number=1,
            task_id="task-1",
            description="Step 1",
            dependencies={2}  # Depends on step 2
        ),
        RunbookStep(
            step_number=2,
            task_id="task-2",
            description="Step 2",
            dependencies={1}  # Depends on step 1 - circular!
        )
    ]
    
    with pytest.raises(ValueError, match="circular"):
        runbook_manager.create_runbook(
            name="Circular Runbook",
            description="Test",
            steps=steps,
            created_by="operator-123"
        )


def test_create_runbook_self_dependency(runbook_manager):
    """Test that self-dependencies are detected"""
    steps = [
        RunbookStep(
            step_number=1,
            task_id="task-1",
            description="Step 1",
            dependencies={1}  # Depends on itself
        )
    ]
    
    with pytest.raises(ValueError, match="cannot depend on itself"):
        runbook_manager.create_runbook(
            name="Self-Dep Runbook",
            description="Test",
            steps=steps,
            created_by="operator-123"
        )


def test_create_runbook_forward_dependency(runbook_manager):
    """Test that forward dependencies are detected"""
    steps = [
        RunbookStep(
            step_number=1,
            task_id="task-1",
            description="Step 1",
            dependencies={2}  # Depends on later step
        ),
        RunbookStep(
            step_number=2,
            task_id="task-2",
            description="Step 2"
        )
    ]
    
    with pytest.raises(ValueError, match="cannot depend on step 2"):
        runbook_manager.create_runbook(
            name="Forward-Dep Runbook",
            description="Test",
            steps=steps,
            created_by="operator-123"
        )


def test_get_runbook(runbook_manager, simple_steps):
    """Test getting a runbook by ID"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    runbook = runbook_manager.get_runbook(runbook_id)
    assert runbook is not None
    assert runbook.runbook_id == runbook_id


def test_get_runbook_nonexistent(runbook_manager):
    """Test getting nonexistent runbook returns None"""
    runbook = runbook_manager.get_runbook(uuid4())
    assert runbook is None


def test_get_runbook_specific_version(runbook_manager, simple_steps):
    """Test getting a specific version of a runbook"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    # Update to create version 2
    runbook_manager.update_runbook(
        runbook_id=runbook_id,
        updates={"description": "Updated"},
        updated_by="operator-456"
    )
    
    # Get version 1
    v1 = runbook_manager.get_runbook(runbook_id, version=1)
    assert v1.version == 1
    assert v1.description == "Test"
    
    # Get version 2
    v2 = runbook_manager.get_runbook(runbook_id, version=2)
    assert v2.version == 2
    assert v2.description == "Updated"


def test_update_runbook(runbook_manager, simple_steps):
    """Test updating a runbook creates new version"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Original",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    updated = runbook_manager.update_runbook(
        runbook_id=runbook_id,
        updates={"description": "Updated description"},
        updated_by="operator-456"
    )
    
    assert updated.version == 2
    assert updated.description == "Updated description"
    assert updated.updated_by == "operator-456"
    
    # Original version should still exist
    v1 = runbook_manager.get_runbook(runbook_id, version=1)
    assert v1.description == "Original"


def test_update_runbook_nonexistent(runbook_manager):
    """Test updating nonexistent runbook raises ValueError"""
    with pytest.raises(ValueError, match="not found"):
        runbook_manager.update_runbook(
            runbook_id=uuid4(),
            updates={"description": "Test"},
            updated_by="operator-123"
        )


def test_update_runbook_invalid_structure(runbook_manager, simple_steps):
    """Test updating with invalid structure raises ValueError"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    # Try to update with circular dependency
    invalid_steps = [
        RunbookStep(
            step_number=1,
            task_id="task-1",
            description="Step 1",
            dependencies={2}
        ),
        RunbookStep(
            step_number=2,
            task_id="task-2",
            description="Step 2",
            dependencies={1}
        )
    ]
    
    with pytest.raises(ValueError, match="circular"):
        runbook_manager.update_runbook(
            runbook_id=runbook_id,
            updates={"steps": invalid_steps},
            updated_by="operator-456"
        )


def test_execute_runbook(runbook_manager, simple_steps):
    """Test starting runbook execution"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    robot_id = uuid4()
    execution_id = runbook_manager.execute_runbook(runbook_id, robot_id)
    
    assert execution_id in runbook_manager.executions
    execution = runbook_manager.executions[execution_id]
    assert execution.runbook_id == runbook_id
    assert execution.robot_id == robot_id
    assert execution.status == "IN_PROGRESS"


def test_execute_runbook_nonexistent(runbook_manager):
    """Test executing nonexistent runbook raises ValueError"""
    with pytest.raises(ValueError, match="not found"):
        runbook_manager.execute_runbook(uuid4(), uuid4())


def test_execute_runbook_updates_usage_stats(runbook_manager, simple_steps):
    """Test that execution updates usage statistics"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    stats_before = runbook_manager.get_usage_stats(runbook_id)
    assert stats_before.total_executions == 0
    
    runbook_manager.execute_runbook(runbook_id, uuid4())
    
    stats_after = runbook_manager.get_usage_stats(runbook_id)
    assert stats_after.total_executions == 1
    assert stats_after.last_executed is not None


def test_record_step_completion(runbook_manager, simple_steps):
    """Test recording step completion"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    execution_id = runbook_manager.execute_runbook(runbook_id, uuid4())
    trace_id = uuid4()
    
    runbook_manager.record_step_completion(execution_id, 1, trace_id, success=True)
    
    execution = runbook_manager.executions[execution_id]
    assert 1 in execution.completed_steps
    assert execution.execution_traces[1] == trace_id


def test_record_step_failure(runbook_manager, simple_steps):
    """Test recording step failure"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    execution_id = runbook_manager.execute_runbook(runbook_id, uuid4())
    trace_id = uuid4()
    
    runbook_manager.record_step_completion(execution_id, 1, trace_id, success=False)
    
    execution = runbook_manager.executions[execution_id]
    assert 1 in execution.failed_steps
    assert 1 not in execution.completed_steps


def test_record_step_skipped(runbook_manager, simple_steps):
    """Test recording skipped step"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    execution_id = runbook_manager.execute_runbook(runbook_id, uuid4())
    
    runbook_manager.record_step_skipped(execution_id, 2)
    
    execution = runbook_manager.executions[execution_id]
    assert 2 in execution.skipped_steps


def test_complete_execution_success(runbook_manager, simple_steps):
    """Test completing execution successfully"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    execution_id = runbook_manager.execute_runbook(runbook_id, uuid4())
    runbook_manager.complete_execution(execution_id, "COMPLETED")
    
    execution = runbook_manager.executions[execution_id]
    assert execution.status == "COMPLETED"
    assert execution.completed_at is not None
    
    stats = runbook_manager.get_usage_stats(runbook_id)
    assert stats.successful_executions == 1
    assert stats.success_rate == 1.0


def test_complete_execution_failure(runbook_manager, simple_steps):
    """Test completing execution with failure"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    execution_id = runbook_manager.execute_runbook(runbook_id, uuid4())
    runbook_manager.complete_execution(execution_id, "FAILED")
    
    execution = runbook_manager.executions[execution_id]
    assert execution.status == "FAILED"
    
    stats = runbook_manager.get_usage_stats(runbook_id)
    assert stats.failed_executions == 1
    assert stats.success_rate == 0.0


def test_usage_stats_success_rate(runbook_manager, simple_steps):
    """Test that success rate is calculated correctly"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    # Execute 3 times: 2 success, 1 failure
    for i in range(3):
        execution_id = runbook_manager.execute_runbook(runbook_id, uuid4())
        status = "COMPLETED" if i < 2 else "FAILED"
        runbook_manager.complete_execution(execution_id, status)
    
    stats = runbook_manager.get_usage_stats(runbook_id)
    assert stats.total_executions == 3
    assert stats.successful_executions == 2
    assert stats.failed_executions == 1
    assert abs(stats.success_rate - 0.6667) < 0.01


def test_usage_stats_average_duration(runbook_manager, simple_steps):
    """Test that average duration is calculated correctly"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    # Execute twice with known durations
    execution_id1 = runbook_manager.execute_runbook(runbook_id, uuid4())
    execution1 = runbook_manager.executions[execution_id1]
    execution1.started_at = datetime.utcnow() - timedelta(seconds=10)
    runbook_manager.complete_execution(execution_id1, "COMPLETED")
    
    execution_id2 = runbook_manager.execute_runbook(runbook_id, uuid4())
    execution2 = runbook_manager.executions[execution_id2]
    execution2.started_at = datetime.utcnow() - timedelta(seconds=20)
    runbook_manager.complete_execution(execution_id2, "COMPLETED")
    
    stats = runbook_manager.get_usage_stats(runbook_id)
    # Average should be around 15 seconds
    assert 14 < stats.average_duration_seconds < 16


def test_validate_runbook(runbook_manager, simple_steps):
    """Test runbook validation"""
    runbook = Runbook(
        runbook_id=uuid4(),
        name="Test",
        description="Test",
        version=1,
        steps=simple_steps,
        created_at=datetime.utcnow(),
        created_by="test",
        updated_at=datetime.utcnow(),
        updated_by="test"
    )
    
    result = runbook_manager.validate_runbook(runbook)
    assert result.is_valid
    assert len(result.errors) == 0


def test_validate_runbook_unknown_task(runbook_manager):
    """Test validation fails for unknown tasks"""
    steps = [
        RunbookStep(
            step_number=1,
            task_id="unknown-task",
            description="Invalid"
        )
    ]
    
    runbook = Runbook(
        runbook_id=uuid4(),
        name="Test",
        description="Test",
        version=1,
        steps=steps,
        created_at=datetime.utcnow(),
        created_by="test",
        updated_at=datetime.utcnow(),
        updated_by="test"
    )
    
    result = runbook_manager.validate_runbook(runbook)
    assert not result.is_valid
    assert any("unknown task" in err.lower() for err in result.errors)


def test_list_runbooks(runbook_manager, simple_steps):
    """Test listing all runbooks"""
    runbook_manager.create_runbook(
        name="Runbook A",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    runbook_manager.create_runbook(
        name="Runbook B",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    runbooks = runbook_manager.list_runbooks()
    assert len(runbooks) == 2
    assert runbooks[0].name == "Runbook A"  # Sorted by name
    assert runbooks[1].name == "Runbook B"


def test_list_runbooks_by_tags(runbook_manager, simple_steps):
    """Test listing runbooks filtered by tags"""
    runbook_manager.create_runbook(
        name="Safety Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123",
        tags={"safety", "production"}
    )
    
    runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123",
        tags={"test"}
    )
    
    safety_runbooks = runbook_manager.list_runbooks(tags={"safety"})
    assert len(safety_runbooks) == 1
    assert safety_runbooks[0].name == "Safety Runbook"


def test_get_execution(runbook_manager, simple_steps):
    """Test getting execution by ID"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    execution_id = runbook_manager.execute_runbook(runbook_id, uuid4())
    execution = runbook_manager.get_execution(execution_id)
    
    assert execution is not None
    assert execution.execution_id == execution_id


def test_list_executions(runbook_manager, simple_steps):
    """Test listing executions"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    robot_id = uuid4()
    runbook_manager.execute_runbook(runbook_id, robot_id)
    runbook_manager.execute_runbook(runbook_id, uuid4())
    
    all_executions = runbook_manager.list_executions()
    assert len(all_executions) == 2
    
    robot_executions = runbook_manager.list_executions(robot_id=robot_id)
    assert len(robot_executions) == 1


def test_list_executions_by_status(runbook_manager, simple_steps):
    """Test listing executions filtered by status"""
    runbook_id = runbook_manager.create_runbook(
        name="Test Runbook",
        description="Test",
        steps=simple_steps,
        created_by="operator-123"
    )
    
    exec1 = runbook_manager.execute_runbook(runbook_id, uuid4())
    exec2 = runbook_manager.execute_runbook(runbook_id, uuid4())
    
    runbook_manager.complete_execution(exec1, "COMPLETED")
    runbook_manager.complete_execution(exec2, "FAILED")
    
    completed = runbook_manager.list_executions(status="COMPLETED")
    assert len(completed) == 1
    
    failed = runbook_manager.list_executions(status="FAILED")
    assert len(failed) == 1
