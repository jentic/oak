#!/usr/bin/env python3
"""
Tests for WorkflowExecutionResult and related functionality

This module tests the WorkflowExecutionResult class and the error context
functionality in the output extractor.
"""

import unittest
from typing import Any, Dict

from oak_runner.models import WorkflowExecutionResult, WorkflowExecutionStatus
from oak_runner.executor.output_extractor import OutputExtractor


class TestWorkflowExecutionResult(unittest.TestCase):
    """Test the WorkflowExecutionResult class"""

    def test_initialization(self):
        """Test that WorkflowExecutionResult initializes correctly"""
        # Basic initialization with required fields
        result = WorkflowExecutionResult(
            status=WorkflowExecutionStatus.WORKFLOW_COMPLETE,
            workflow_id="test_workflow"
        )
        self.assertEqual(result.status, WorkflowExecutionStatus.WORKFLOW_COMPLETE)
        self.assertEqual(result.workflow_id, "test_workflow")
        self.assertEqual(result.outputs, {})
        self.assertIsNone(result.step_outputs)
        self.assertIsNone(result.inputs)
        self.assertIsNone(result.error)

        # Full initialization with all fields
        step_outputs = {
            "step1": {"output1": "value1"},
            "step2": {"output2": "value2"}
        }
        inputs = {"param1": "value1", "param2": 123}
        result = WorkflowExecutionResult(
            status=WorkflowExecutionStatus.ERROR,
            workflow_id="test_workflow",
            outputs={"result": "test_output"},
            step_outputs=step_outputs,
            inputs=inputs,
            error="Test error message"
        )
        self.assertEqual(result.status, WorkflowExecutionStatus.ERROR)
        self.assertEqual(result.workflow_id, "test_workflow")
        self.assertEqual(result.outputs, {"result": "test_output"})
        self.assertEqual(result.step_outputs, step_outputs)
        self.assertEqual(result.inputs, {"param1": "value1", "param2": 123})
        self.assertEqual(result.error, "Test error message")


class TestErrorContext(unittest.TestCase):
    """Test the error context functionality in the output extractor"""

    def test_error_context_for_non_2xx_status(self):
        """Test that error context is added for non-2xx status codes"""
        extractor = OutputExtractor({})
        
        # Test with a 400 status code
        response = {
            "status_code": 400,
            "headers": {"Content-Type": "application/json"},
            "body": {"error": "Bad Request", "message": "Invalid input"}
        }
        step = {"stepId": "test_step"}
        
        outputs = extractor.extract_outputs(step, response, {})
        
        self.assertIn("oak_error_context", outputs)
        self.assertEqual(outputs["oak_error_context"]["http_code"], 400)
        self.assertEqual(outputs["oak_error_context"]["http_response"], response["body"])
        
        # Test with a 500 status code
        response = {
            "status_code": 500,
            "headers": {"Content-Type": "application/json"},
            "body": {"error": "Internal Server Error"}
        }
        
        outputs = extractor.extract_outputs(step, response, {})
        
        self.assertIn("oak_error_context", outputs)
        self.assertEqual(outputs["oak_error_context"]["http_code"], 500)
        self.assertEqual(outputs["oak_error_context"]["http_response"], response["body"])

    def test_no_error_context_for_2xx_status(self):
        """Test that error context is not added for 2xx status codes"""
        extractor = OutputExtractor({})
        
        # Test with a 200 status code
        response = {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {"data": "Success"}
        }
        step = {"stepId": "test_step"}
        
        outputs = extractor.extract_outputs(step, response, {})
        
        self.assertNotIn("oak_error_context", outputs)
        
        # Test with a 201 status code
        response = {
            "status_code": 201,
            "headers": {"Content-Type": "application/json"},
            "body": {"data": "Created"}
        }
        
        outputs = extractor.extract_outputs(step, response, {})
        
        self.assertNotIn("oak_error_context", outputs)
        
    def test_explicit_none_values(self):
        """Test that explicitly setting optional fields to None works correctly"""
        # Create a result with explicit None values
        result = WorkflowExecutionResult(
            status=WorkflowExecutionStatus.WORKFLOW_COMPLETE,
            workflow_id="test_workflow",
            outputs={"result": "test_output"},
            step_outputs=None,
            inputs=None,
            error=None
        )
        
        # Verify the fields are correctly set
        self.assertEqual(result.status, WorkflowExecutionStatus.WORKFLOW_COMPLETE)
        self.assertEqual(result.workflow_id, "test_workflow")
        self.assertEqual(result.outputs, {"result": "test_output"})
        self.assertIsNone(result.step_outputs)
        self.assertIsNone(result.inputs)
        self.assertIsNone(result.error)


class TestIntegration(unittest.TestCase):
    """Integration tests for workflow execution result and error context"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.step_outputs = {
            "step1": {"output1": "value1"},
            "step2": {
                "output2": "value2",
                "oak_error_context": {
                    "http_code": 404,
                    "http_response": {"error": "Not Found"}
                }
            }
        }
    
    def test_error_context_in_workflow_result(self):
        """Test that error context is properly included in workflow execution result"""
        inputs = {"user_id": "12345", "message": "Hello world"}
        result = WorkflowExecutionResult(
            status=WorkflowExecutionStatus.ERROR,
            workflow_id="test_workflow",
            outputs={"result": "test_output"},
            step_outputs=self.step_outputs,
            inputs=inputs,
            error="Step failed success criteria"
        )
        
        # Verify the error context is accessible in the step outputs
        self.assertIn("oak_error_context", result.step_outputs["step2"])
        error_context = result.step_outputs["step2"]["oak_error_context"]
        self.assertEqual(error_context["http_code"], 404)
        self.assertEqual(error_context["http_response"], {"error": "Not Found"})


if __name__ == "__main__":
    unittest.main()
