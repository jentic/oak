import pytest
from oak_runner.evaluator import ExpressionEvaluator
from oak_runner.models import ExecutionState

@pytest.fixture
def state():
    # Simulate the in-memory state as it exists after a step runs
    s = ExecutionState(workflow_id="demo")
    s.step_outputs = {
        "findPetsStep": {
            "statusCode": 200,
            "responseBody": [{"id": 1}, {"id": 2}]
        }
    }
    return s

@pytest.mark.parametrize("expr,expected", [
    # Root-dot normalization: should handle leading '$.'
    ("$.steps.findPetsStep.statusCode", 200),
    # Redundant 'outputs' segment: should skip 'outputs' if not present in dict
    ("$.steps.findPetsStep.outputs.statusCode", 200),
    ("$steps.findPetsStep.outputs.statusCode", 200),
    # Both fixes together: verbose form with array output
    ("$.steps.findPetsStep.outputs.responseBody", [{"id": 1}, {"id": 2}]),
])
def test_evaluator_path_variants(state, expr, expected):
    result = ExpressionEvaluator.evaluate_expression(expr, state)
    assert result == expected, f"Expression '{expr}' should resolve to {expected}, got {result}"