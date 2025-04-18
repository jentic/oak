"""
Command-line interface for the Arazzo workflow runner.
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from .runner import OAKRunner
from .models import StepStatus 
from .utils import set_log_level

logger = logging.getLogger("oak-runner-cli")


def parse_inputs(inputs_str: str) -> dict[str, Any]:
    """Parse input string into a dictionary."""
    if not inputs_str:
        return {}
    try:
        inputs = json.loads(inputs_str)
        if not isinstance(inputs, dict):
            raise ValueError("Inputs must be a JSON object (dictionary).")
        return inputs
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format for inputs: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Oak Runner")
    # Global arguments - defined *before* subparsers
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: WARNING)",
    )

    subparsers = parser.add_subparsers(dest="operation", required=True, help='Operation to perform')

    # Subparser for 'show-env-mappings'
    parser_env = subparsers.add_parser('show-env-mappings', help='Show environment variable mappings for authentication')
    # Group to require one path source
    env_path_group = parser_env.add_mutually_exclusive_group(required=True)
    env_path_group.add_argument(
        "arazzo_path",
        nargs='?', # Make positional optional *within the group*
        default=None, # Explicitly default to None
        help="Path to the Arazzo YAML file to provide context (use this OR --openapi-path)"
    )
    env_path_group.add_argument(
        "--openapi-path",
        help="Path to the OpenAPI spec file to provide context (use this OR arazzo_path)"
    )
    parser_env.set_defaults(func=handle_show_env_mappings)

    # Subparser for 'execute-workflow'
    parser_exec_wf = subparsers.add_parser('execute-workflow', help='Execute a complete workflow')
    parser_exec_wf.add_argument(
        "arazzo_path",
        help="Path to the Arazzo YAML file" # Required for this command
    )
    parser_exec_wf.add_argument("--workflow-id", required=True, help="ID of the workflow to execute")
    parser_exec_wf.add_argument("--inputs", help="JSON string of workflow inputs", default="{}")
    parser_exec_wf.set_defaults(func=handle_execute_workflow)

    # Subparser for 'execute-operation'
    parser_exec_op = subparsers.add_parser('execute-operation', help='Execute a single API operation directly')
    # Use mutually exclusive group for path specifiers
    path_group = parser_exec_op.add_mutually_exclusive_group(required=True)
    path_group.add_argument(
        "--arazzo-path",
        help="Path to the Arazzo YAML file containing the operation definition"
    )
    path_group.add_argument(
        "--openapi-path",
        help="Path to the OpenAPI spec file containing the operation definition"
    )
    # Operation identifiers
    exec_group = parser_exec_op.add_mutually_exclusive_group(required=True)
    exec_group.add_argument("--operation-id", help="ID of the operation to execute")
    exec_group.add_argument("--operation-path", help="HTTP method and path (e.g., 'GET /users/{id}')")
    parser_exec_op.add_argument("--inputs", default="{}", help="Inputs for the operation as a JSON string")
    parser_exec_op.set_defaults(func=handle_execute_operation)

    # Subparser for 'list-workflows'
    parser_list_wf = subparsers.add_parser('list-workflows', help='List all workflow IDs in an Arazzo file')
    parser_list_wf.add_argument("arazzo_path", help="Path to the Arazzo YAML file")
    parser_list_wf.set_defaults(func=handle_list_workflows)

    # Subparser for 'describe-workflow'
    parser_desc_wf = subparsers.add_parser('describe-workflow', help='Show details of a specific workflow')
    parser_desc_wf.add_argument("arazzo_path", help="Path to the Arazzo YAML file")
    parser_desc_wf.add_argument("--workflow-id", required=True, help="ID of the workflow to describe")
    parser_desc_wf.set_defaults(func=handle_describe_workflow)

    # Subparser for 'generate-example'
    parser_gen_ex = subparsers.add_parser('generate-example', help='Generate an example execution command for a workflow')
    parser_gen_ex.add_argument("arazzo_path", help="Path to the Arazzo YAML file")
    parser_gen_ex.add_argument("--workflow-id", required=True, help="ID of the workflow to generate example for")
    parser_gen_ex.set_defaults(func=handle_generate_example)

    args = parser.parse_args()

    # Set log level early
    set_log_level(args.log_level)

    # Adjust log level based on command or explicit flag
    # Suppress logs for inspection commands unless overridden
    if args.operation in ["list-workflows", "describe-workflow", "generate-example"] and args.log_level == "INFO":
         # Suppress standard INFO/DEBUG logs for these commands by default
         set_log_level("WARNING")
    else:
         # Use the specified or default log level for other commands
         set_log_level(args.log_level)

    # Removed argument validation section as it's handled by argparse structure now

    runner = None # Runner will be initialized within handlers now
    try:
        # --- Command Execution ---
        # Call the function associated with the chosen subparser
        # Pass runner (always None initially) and args to the handler
        # The handler function is responsible for ensuring the runner is initialized.
        if hasattr(args, 'func'):
            await args.func(None, args) # Pass None for runner
        else:
            # Should not happen due to required=True on subparsers
            parser.print_help()
            sys.exit(1)

    except ValueError as e:
        logger.error(f"Input Error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"File Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


async def handle_show_env_mappings(runner: OAKRunner | None, args: argparse.Namespace):
    # Runner is always passed as None now, initialize here based on args
    logger.info("Fetching environment variable mappings...")
    try:
        # Initialize runner based on provided path
        if args.arazzo_path:
            logger.info(f"Initializing runner with Arazzo file: {args.arazzo_path}")
            runner = OAKRunner.from_arazzo_path(args.arazzo_path)
        elif args.openapi_path:
            logger.info(f"Initializing runner with OpenAPI file: {args.openapi_path}")
            runner = OAKRunner.from_openapi_path(args.openapi_path)
        else:
            # This case should be prevented by the required mutually exclusive group
            logger.error("Cannot fetch environment mappings: No Arazzo or OpenAPI path specified.")
            sys.exit(1)

        # Ensure runner got initialized successfully
        if not runner:
             logger.error("Runner initialization failed.")
             sys.exit(1)

        mappings = runner.get_env_mappings()
        print(json.dumps(mappings, indent=2))
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to get environment mappings: {e}", exc_info=True)
        sys.exit(1)


async def handle_execute_workflow(runner: OAKRunner | None, args: argparse.Namespace):
    # Runner is always passed as None now, initialize here
    logger.info("Executing workflow...")
    # Initialize runner
    if not args.arazzo_path:
         # Should be caught by argparse, but defensive check
         logger.error("Arazzo path is required for execute-workflow.")
         sys.exit(1)
    logger.info(f"Initializing runner with Arazzo file: {args.arazzo_path}")
    runner = OAKRunner.from_arazzo_path(args.arazzo_path)
    if not runner:
        logger.error("Runner initialization failed.")
        sys.exit(1)

    # Parse inputs
    try:
        inputs = json.loads(args.inputs)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in inputs: {args.inputs}")
        sys.exit(1)

    if not args.workflow_id:
        logger.error("--workflow-id is required for execute-workflow.")
        sys.exit(1)

    # Start and execute the workflow using the new API
    try:
        outputs = runner.execute_workflow(args.workflow_id, inputs)
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}", exc_info=True)
        sys.exit(1)

    # Print outputs and determine success/failure
    print(f"\n=== Completed workflow: {args.workflow_id} ===")
    print(f"Outputs: {json.dumps(outputs, indent=2)}")

    # Check for failure in outputs (if possible)
    try:
        state = None
        for exec_id, st in runner.execution_states.items():
            if st.workflow_id == args.workflow_id:
                state = st
                break
        if not state:
            logger.error(f"Could not retrieve final execution state for {args.workflow_id}")
            sys.exit(1)
        last_step_id = list(state.status.keys())[-1] if state.status else None
        all_success = not (last_step_id and state.status.get(last_step_id) == StepStatus.FAILURE)
    except Exception as e:
        logger.error(f"Error determining final workflow status: {e}", exc_info=True)
        all_success = False

    sys.exit(0 if all_success else 1)


async def handle_execute_operation(runner: OAKRunner | None, args: argparse.Namespace): # Runner can be None initially
    """Handles the execute_operation command."""
    # Runner is always passed as None now, initialize here
    logger.info("Executing direct operation...")
    try:
        # Initialize runner based on provided path
        if args.arazzo_path:
             logger.info(f"Initializing runner with Arazzo file: {args.arazzo_path}")
             runner = OAKRunner.from_arazzo_path(args.arazzo_path)
        elif args.openapi_path:
             logger.info(f"Initializing runner with OpenAPI file: {args.openapi_path}")
             runner = OAKRunner.from_openapi_path(args.openapi_path)
        else:
             # This state should be prevented by the mutually exclusive group requirement
             logger.error("Cannot execute operation: No Arazzo or OpenAPI path specified.")
             sys.exit(1)

        # Ensure runner got initialized successfully
        if not runner:
            logger.error("Runner initialization failed.")
            sys.exit(1)

        inputs = json.loads(args.inputs)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in inputs: {args.inputs}")
        sys.exit(1)

    try:
        # Ensure runner is valid before calling execute_operation
        if not runner:
            logger.error("Runner was not initialized correctly.")
            sys.exit(1)
            
        # Correctly pass operation_id and operation_path based on args
        # REMOVED await as execute_operation is synchronous
        result = runner.execute_operation(
            operation_id=args.operation_id,  # Pass directly
            operation_path=args.operation_path, # Pass directly
            inputs=inputs
        )
        # Remove 'headers' from result if present
        if isinstance(result, dict) and 'headers' in result:
            result = dict(result)  # Make a shallow copy to avoid mutating originals
            result.pop('headers')
        logger.info(f"Operation Result: {json.dumps(result, indent=2)}")
        # Determine exit code based on HTTP status (e.g., 2xx is success)
        status_code = result.get("status_code", 500)
        sys.exit(0 if 200 <= status_code < 300 else 1)

    except Exception as e:
        logger.error(f"Failed to execute operation: {e}", exc_info=True)
        sys.exit(1)


async def handle_list_workflows(runner: OAKRunner | None, args: argparse.Namespace):
    """Handles the list-workflows command using logic from old arazzo_runner."""
    # logger.info("Listing workflows...") # Suppressed for this command by default
    try:
        if not args.arazzo_path:
            logger.error("Arazzo path is required for list-workflows.")
            sys.exit(1)
        # Initialize runner to access Arazzo data
        runner = OAKRunner.from_arazzo_path(args.arazzo_path)
        # Check runner and runner.arazzo_doc
        if not runner or not runner.arazzo_doc:
            logger.error("Runner initialization or Arazzo doc loading failed.")
            sys.exit(1)

        # --- Logic copied from arazzo_runner ---
        workflows = runner.arazzo_doc.get("workflows", [])
        if not workflows:
            print("No workflows found in the Arazzo document.")
            sys.exit(0)
        print("Available Workflows:")
        for workflow in workflows:
            workflow_id = workflow.get("workflowId", "Unknown")
            description = workflow.get("description", "No description available")
            print(f"- {workflow_id}: {description}")
        # --- End copied logic ---
        sys.exit(0)
    except Exception as e:
        # Use logger for exceptions even if standard output is suppressed
        logging.getLogger("oak-runner-cli").error(f"Failed to list workflows: {e}", exc_info=True)
        sys.exit(1)


async def handle_describe_workflow(runner: OAKRunner | None, args: argparse.Namespace):
    """Handles the describe-workflow command using logic from old arazzo_runner."""
    # logger.info(f"Describing workflow: {args.workflow_id}") # Suppressed
    try:
        if not args.arazzo_path:
            logger.error("Arazzo path is required for describe-workflow.")
            sys.exit(1)
        if not args.workflow_id:
            # Use print for user-facing errors in suppressed-log commands
            print("Error: --workflow-id is required for the describe-workflow operation")
            sys.exit(1)

        # Initialize runner to access Arazzo data
        runner = OAKRunner.from_arazzo_path(args.arazzo_path)
        # Check runner and runner.arazzo_doc
        if not runner or not runner.arazzo_doc:
            logger.error("Runner initialization or Arazzo doc loading failed.")
            sys.exit(1)

        # --- Logic copied from arazzo_runner ---
        workflows = runner.arazzo_doc.get("workflows", [])
        target_workflow = None
        for workflow in workflows:
            if workflow.get("workflowId") == args.workflow_id:
                target_workflow = workflow
                break
        if not target_workflow:
            print(f"Error: Workflow with ID '{args.workflow_id}' not found in the Arazzo document")
            sys.exit(1)

        # Display workflow details
        print(f"Workflow: {target_workflow.get('workflowId')}")
        print(f"Summary: {target_workflow.get('description', 'No description available')}")
        # Display input parameters
        inputs_schema = target_workflow.get("inputs", {})
        if inputs_schema and "properties" in inputs_schema:
            properties = inputs_schema.get("properties", {})
            print("\nInputs:")
            for param_name, param_details in properties.items():
                param_type = param_details.get("type", "string")
                description = param_details.get("description", "")
                print(f"- {param_name} ({param_type}): {description}")
        # Display workflow steps
        steps = target_workflow.get("steps", [])
        if steps:
            print("\nSteps:")
            for i, step in enumerate(steps, 1):
                step_id = step.get("stepId", "Unknown")
                description = step.get("description", "")
                if description:
                    print(f"{i}. {step_id}: {description}")
                else:
                    print(f"{i}. {step_id}")
        # Display workflow outputs
        output_mappings = target_workflow.get("outputs", {})
        if output_mappings:
            print("\nOutputs:")
            for output_name in output_mappings.keys():
                print(f"- {output_name}")
        # --- End copied logic ---
        sys.exit(0)
    except Exception as e:
        logging.getLogger("oak-runner-cli").error(f"Failed to describe workflow: {e}", exc_info=True)
        sys.exit(1)


async def handle_generate_example(runner: OAKRunner | None, args: argparse.Namespace):
    """Handles the generate-example command using logic from old arazzo_runner."""
    # logger.info(f"Generating example command for workflow: {args.workflow_id}") # Suppressed
    try:
        if not args.arazzo_path:
            logger.error("Arazzo path is required for generate-example.")
            sys.exit(1)
        if not args.workflow_id:
            print("Error: --workflow-id is required for the generate-example operation")
            sys.exit(1)

        # Initialize runner to access Arazzo data
        runner = OAKRunner.from_arazzo_path(args.arazzo_path)
         # Check runner and runner.arazzo_doc
        if not runner or not runner.arazzo_doc:
             logger.error("Runner initialization or Arazzo doc loading failed.")
             sys.exit(1)

        # --- Logic copied from arazzo_runner ---
        workflows = runner.arazzo_doc.get("workflows", [])
        target_workflow = None
        for workflow in workflows:
            if workflow.get("workflowId") == args.workflow_id:
                target_workflow = workflow
                break
        if not target_workflow:
            print(f"Error: Workflow with ID '{args.workflow_id}' not found in the Arazzo document")
            sys.exit(1)

        # Generate input placeholders
        inputs_schema = target_workflow.get("inputs", {})
        input_json = {}
        if inputs_schema and "properties" in inputs_schema:
            properties = inputs_schema.get("properties", {})
            # required = inputs_schema.get("required", []) # Not used in original logic
            for param_name, param_details in properties.items():
                param_type = param_details.get("type", "string")
                # Generate appropriate placeholder based on parameter type
                if param_type == "string":
                    if "id" in param_name.lower():
                        placeholder = f"YOUR_{param_name.upper()}"
                    else:
                        placeholder = f"Your {param_name.replace('_', ' ')} here"
                elif param_type == "integer" or param_type == "number":
                    placeholder = 0
                elif param_type == "boolean":
                    placeholder = False
                elif param_type == "array":
                    placeholder = []
                elif param_type == "object":
                    placeholder = {}
                else:
                    placeholder = "PLACEHOLDER"
                input_json[param_name] = placeholder

        # Format the command example using the correct OAK Runner CLI format
        file_path = args.arazzo_path
        # Escape quotes twice for shell embedding (once for JSON, once for shell)
        inputs_json_string = json.dumps(input_json).replace('"', '\\"')
        example_cmd = (
            f"pdm run python -m oak_runner execute-workflow "
            f"{file_path} "
            f"--workflow-id {args.workflow_id} "
            f"--inputs \"{inputs_json_string}\""
        )
        print(example_cmd)
        # --- End copied logic ---
        sys.exit(0)

    except KeyError: # Added specific catch if workflow not found during input generation
         print(f"Error: Workflow ID '{args.workflow_id}' not found when generating example.")
         sys.exit(1)
    except Exception as e:
        logging.getLogger("oak-runner-cli").error(f"Failed to generate example: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
