#!/usr/bin/env python3
"""
OAK Runner Data Models

This module defines the data models and enums used by the OAK Runner.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

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
