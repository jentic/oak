#!/usr/bin/env python3
"""
OAK Runner Data Models

This module defines the data models and enums used by the OAK Runner.
"""

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any, Dict, Optional

OpenAPIDoc = Dict[str, Any]
ArazzoDoc = Dict[str, Any]


class StepStatus(Enum):
    """Status of a workflow step execution"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class ActionType(Enum):
    """Type of action to take after a step execution"""

    CONTINUE = "continue"  # Continue to next step
    END = "end"  # End workflow
    GOTO = "goto"  # Go to another step or workflow
    RETRY = "retry"  # Retry the current step


class WorkflowExecutionStatus(StrEnum):
    """Represents the status strings returned by OAK Runner execution logic."""

    WORKFLOW_COMPLETE = "workflow_complete"
    ERROR = "error"
    GOTO_WORKFLOW = "goto_workflow"
    GOTO_STEP = "goto_step"
    RETRY = "retry"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value


@dataclass
class WorkflowExecutionResult:
    """Represents the result of a workflow execution
    
    This class models the structure of the result returned by the execute_workflow method.
    
    Attributes:
        status: The status of the workflow execution (e.g., WORKFLOW_COMPLETE, ERROR)
        workflow_id: The ID of the executed workflow
        outputs: The outputs produced by the workflow
        step_outputs: The outputs from each step in the workflow
        inputs: The original inputs provided to the workflow
        error: Optional error message if the workflow execution failed
    """
    status: WorkflowExecutionStatus
    workflow_id: str
    outputs: dict[str, Any] = field(default_factory=dict)
    step_outputs: Optional[dict[str, dict[str, Any]]] = None
    inputs: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ExecutionState:
    """Represents the current execution state of a workflow"""

    workflow_id: str
    current_step_id: str | None = None
    inputs: dict[str, Any] = None
    step_outputs: dict[str, dict[str, Any]] = None
    workflow_outputs: dict[str, Any] = None
    dependency_outputs: dict[str, dict[str, Any]] = None
    status: dict[str, StepStatus] = None

    def __post_init__(self):
        """Initialize default values"""
        if self.inputs is None:
            self.inputs = {}
        if self.step_outputs is None:
            self.step_outputs = {}
        if self.workflow_outputs is None:
            self.workflow_outputs = {}
        if self.dependency_outputs is None:
            self.dependency_outputs = {}
        if self.status is None:
            self.status = {}
