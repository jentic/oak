#!/usr/bin/env python3
"""
Executor module for OAK Runner

This module has been refactored into a package for better maintainability.
See the executor/ directory for the actual implementation.
"""

from .executor.step_executor import StepExecutor

# Re-export the StepExecutor class for backward compatibility
__all__ = ["StepExecutor"]
