from oak_runner.models import WorkflowExecutionStatus


def test_workflow_execution_status_equality_and_representation():
    """
    Tests that WorkflowExecutionStatus enum members are equal to their string values
    and that their string representations are also their plain string values.
    """
    for status_member in WorkflowExecutionStatus:
        # Test direct equality with its string value (due to inheriting str)
        assert status_member == status_member.value

        # Test str() representation
        assert str(status_member) == status_member.value

        # Test repr() representation (since __repr__ is defined as self.value)
        assert repr(status_member) == status_member.value
